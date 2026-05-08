from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import __version__
from .billing import estimate_credits
from .config import get_settings
from .db import create_all, get_db
from .jobs import create_job
from .models import ApiKey, DomainProfile, Job, JobEvent, JobKind, Organization, UsageEvent, User
from .schemas import (
    AdminApiKeyCreate,
    AdminCreditUpdate,
    AdminOrganizationResponse,
    ApiKeyCreate,
    ApiKeyResponse,
    AuthLogin,
    AuthResponse,
    AuthSignup,
    BatchRequest,
    CrawlRequest,
    DomainProfileResponse,
    ExtractRequest,
    JobDetail,
    JobResponse,
    MapRequest,
    ScrapeRequest,
    UsageSummary,
)
from .scraper import map_url, scrape_url
from .security import Principal, create_api_key, hash_api_key, hash_password, require_admin, require_api_key, verify_password
from .seed import seed_admin, seed_demo

settings = get_settings()
app = FastAPI(
    title="Scrapling Cloud API",
    version=__version__,
    description="Firecrawl-inspired scraping, crawling, mapping and extraction API powered by Scrapling.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins + [settings.app_url],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    create_all()
    from .db import SessionLocal

    db = SessionLocal()
    try:
        seed_demo(db)
        seed_admin(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "api", "version": __version__}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    db.execute(select(Job).limit(1))
    return {"ok": True}


def auth_response(raw_key: str, organization: Organization, is_admin: bool = False) -> AuthResponse:
    return AuthResponse(
        api_key=raw_key,
        organization_id=organization.id,
        organization_name=organization.name,
        plan=organization.plan,
        monthly_credits=organization.monthly_credits,
        concurrency_limit=organization.concurrency_limit,
        is_admin=is_admin,
    )


def create_dashboard_key(
    db: Session,
    organization: Organization,
    name: str = "Dashboard session",
    scopes: list[str] | None = None,
) -> str:
    raw_key = create_api_key()
    db.add(
        ApiKey(
            organization_id=organization.id,
            name=name,
            key_prefix=raw_key[:10],
            key_hash=hash_api_key(raw_key),
            scopes=scopes or ["scrape", "crawl", "map", "extract"],
        )
    )
    return raw_key


def job_response(job: Job) -> JobResponse:
    return JobResponse(id=job.id, status=job.status, kind=job.kind, credits=job.credits, url=job.url)


@app.post("/v1/auth/signup", response_model=AuthResponse)
def signup(payload: AuthSignup, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    organization = Organization(name=payload.organization_name.strip(), plan="starter", monthly_credits=10000, concurrency_limit=3)
    db.add(organization)
    db.flush()
    db.add(User(organization_id=organization.id, email=email, password_hash=hash_password(payload.password), role="owner"))
    raw_key = create_dashboard_key(db, organization, "Default dashboard key")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from None
    db.refresh(organization)
    return auth_response(raw_key, organization)


@app.post("/v1/auth/login", response_model=AuthResponse)
def login(payload: AuthLogin, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    organization = db.get(Organization, user.organization_id)
    if organization is None:
        raise HTTPException(status_code=401, detail="Invalid organization")

    scopes = ["scrape", "crawl", "map", "extract"]
    if user.role == "admin":
        scopes = ["admin", *scopes]
    raw_key = create_dashboard_key(db, organization, scopes=scopes)
    db.commit()
    return auth_response(raw_key, organization, is_admin=user.role == "admin")


@app.get("/v1/me", response_model=AuthResponse)
def me(principal: Principal = Depends(require_api_key)) -> AuthResponse:
    return auth_response(principal.api_key.key_prefix, principal.organization, is_admin="admin" in (principal.api_key.scopes or []))


@app.post("/v1/scrape", response_model=JobResponse)
def scrape(
    payload: ScrapeRequest,
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = create_job(db, principal.organization, JobKind.scrape, payload.model_dump(mode="json", by_alias=True))
    return job_response(job)


@app.post("/v1/crawl", response_model=JobResponse)
def crawl(payload: CrawlRequest, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> JobResponse:
    job = create_job(db, principal.organization, JobKind.crawl, payload.model_dump(mode="json", by_alias=True))
    return job_response(job)


@app.post("/v1/map")
async def map_endpoint(
    payload: MapRequest,
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict:
    credits = estimate_credits(JobKind.map.value, payload.model_dump(mode="json", by_alias=True))
    from .billing import reserve_credits

    reserve_credits(db, principal.organization, credits, None, "map_sync")
    db.commit()
    return await map_url(payload.model_dump(mode="json", by_alias=True))


@app.post("/v1/extract", response_model=JobResponse)
def extract(
    payload: ExtractRequest,
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = create_job(db, principal.organization, JobKind.extract, payload.model_dump(mode="json", by_alias=True))
    return job_response(job)


@app.post("/v1/batch", response_model=JobResponse)
def batch(payload: BatchRequest, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> JobResponse:
    job = create_job(db, principal.organization, JobKind.batch, payload.model_dump(mode="json", by_alias=True))
    return job_response(job)


@app.post("/v1/playground/scrape")
async def playground_scrape(payload: ScrapeRequest) -> dict:
    return await scrape_url(payload.model_dump(mode="json", by_alias=True))


@app.get("/v1/jobs", response_model=list[JobResponse])
def list_jobs(principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> list[JobResponse]:
    jobs = db.scalars(
        select(Job).where(Job.organization_id == principal.organization.id).order_by(desc(Job.created_at)).limit(100)
    ).all()
    return [job_response(job) for job in jobs]


@app.get("/v1/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> JobDetail:
    job = db.get(Job, job_id)
    if job is None or job.organization_id != principal.organization.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail(
        id=job.id,
        status=job.status,
        kind=job.kind,
        credits=job.credits,
        url=job.url,
        request=job.request,
        result=job.result,
        error=job.error,
    )


@app.get("/v1/jobs/{job_id}/events")
def job_events(job_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> StreamingResponse:
    job = db.get(Job, job_id)
    if job is None or job.organization_id != principal.organization.id:
        raise HTTPException(status_code=404, detail="Job not found")

    def event_stream():
        events = db.scalars(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at)).all()
        for event in events:
            yield f"event: {event.level}\ndata: {event.message}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/v1/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> list[ApiKeyResponse]:
    keys = db.scalars(select(ApiKey).where(ApiKey.organization_id == principal.organization.id)).all()
    return [
        ApiKeyResponse(
            id=key.id,
            name=key.name,
            prefix=key.key_prefix,
            scopes=key.scopes,
            revoked=key.revoked,
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            created_at=key.created_at.isoformat(),
        )
        for key in keys
    ]


@app.post("/v1/api-keys", response_model=ApiKeyResponse)
def create_key(payload: ApiKeyCreate, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> ApiKeyResponse:
    raw_key = create_api_key()
    api_key = ApiKey(
        organization_id=principal.organization.id,
        name=payload.name,
        key_prefix=raw_key[:10],
        key_hash=hash_api_key(raw_key),
        scopes=payload.scopes,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        revoked=api_key.revoked,
        last_used_at=None,
        created_at=api_key.created_at.isoformat(),
        key=raw_key,
    )


@app.delete("/v1/api-keys/{key_id}")
def revoke_key(key_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    api_key = db.get(ApiKey, key_id)
    if api_key is None or api_key.organization_id != principal.organization.id:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.revoked = True
    db.commit()
    return {"ok": True}


@app.get("/v1/usage", response_model=UsageSummary)
def usage(principal: Principal = Depends(require_api_key)) -> UsageSummary:
    org = principal.organization
    return UsageSummary(
        plan=org.plan,
        monthly_credits=org.monthly_credits,
        used_credits=org.used_credits,
        remaining_credits=max(0, org.monthly_credits - org.used_credits),
        concurrency_limit=org.concurrency_limit,
        is_admin="admin" in (principal.api_key.scopes or []),
    )


def admin_org_response(db: Session, org: Organization) -> AdminOrganizationResponse:
    owner = db.scalar(select(User).where(User.organization_id == org.id).order_by(User.created_at))
    return AdminOrganizationResponse(
        id=org.id,
        name=org.name,
        plan=org.plan,
        monthly_credits=org.monthly_credits,
        used_credits=org.used_credits,
        remaining_credits=max(0, org.monthly_credits - org.used_credits),
        concurrency_limit=org.concurrency_limit,
        owner_email=owner.email if owner else None,
        created_at=org.created_at.isoformat(),
    )


@app.get("/v1/admin/organizations", response_model=list[AdminOrganizationResponse])
def admin_organizations(
    _admin: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminOrganizationResponse]:
    organizations = db.scalars(select(Organization).order_by(desc(Organization.created_at))).all()
    return [admin_org_response(db, org) for org in organizations]


@app.post("/v1/admin/organizations/{organization_id}/credits", response_model=AdminOrganizationResponse)
def admin_update_credits(
    organization_id: str,
    payload: AdminCreditUpdate,
    admin: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminOrganizationResponse:
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    if payload.operation == "add":
        org.monthly_credits += payload.credits
        db.add(UsageEvent(organization_id=org.id, job_id=None, credits=payload.credits, reason=f"admin_credit_add:{admin.organization.id}"))
    elif payload.operation == "set_monthly":
        org.monthly_credits = payload.credits
        db.add(UsageEvent(organization_id=org.id, job_id=None, credits=payload.credits, reason=f"admin_credit_set:{admin.organization.id}"))
    elif payload.operation == "reset_usage":
        org.used_credits = 0
        if payload.credits:
            org.monthly_credits = payload.credits
        db.add(UsageEvent(organization_id=org.id, job_id=None, credits=0, reason=f"admin_usage_reset:{admin.organization.id}"))

    if payload.plan:
        org.plan = payload.plan
    if payload.concurrency_limit is not None:
        org.concurrency_limit = payload.concurrency_limit

    db.commit()
    db.refresh(org)
    return admin_org_response(db, org)


@app.post("/v1/admin/organizations/{organization_id}/api-keys", response_model=ApiKeyResponse)
def admin_create_api_key(
    organization_id: str,
    payload: AdminApiKeyCreate,
    _admin: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiKeyResponse:
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    raw_key = create_api_key()
    api_key = ApiKey(
        organization_id=org.id,
        name=payload.name,
        key_prefix=raw_key[:10],
        key_hash=hash_api_key(raw_key),
        scopes=payload.scopes,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        revoked=api_key.revoked,
        last_used_at=None,
        created_at=api_key.created_at.isoformat(),
        key=raw_key,
    )


@app.get("/v1/domain-profiles", response_model=list[DomainProfileResponse])
def domain_profiles(principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> list[DomainProfileResponse]:
    profiles = db.scalars(select(DomainProfile).where(DomainProfile.organization_id == principal.organization.id)).all()
    return [
        DomainProfileResponse(
            domain=p.domain,
            preferred_mode=p.preferred_mode,
            successful_selectors=p.successful_selectors,
            wait_strategy=p.wait_strategy,
            proxy_success_rate=p.proxy_success_rate,
            failure_reasons=p.failure_reasons,
            recommendations=p.recommendations,
        )
        for p in profiles
    ]


@app.post("/v1/billing/stripe/webhook")
async def stripe_webhook(request: Request) -> dict:
    # Production hook: verify `stripe-signature` with STRIPE_WEBHOOK_SECRET and
    # update plan/customer/subscription fields. This endpoint is kept deployable
    # for Coolify and Stripe setup before live credentials are added.
    payload = await request.body()
    return {"received": True, "bytes": len(payload)}
