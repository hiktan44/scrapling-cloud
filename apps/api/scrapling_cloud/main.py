from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from . import __version__
from .billing import estimate_credits
from .config import get_settings
from .db import create_all, get_db
from .jobs import create_job
from .models import ApiKey, DomainProfile, Job, JobEvent, JobKind
from .schemas import (
    ApiKeyCreate,
    ApiKeyResponse,
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
from .security import Principal, create_api_key, hash_api_key, require_api_key
from .seed import seed_demo

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
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "api", "version": __version__}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    db.execute(select(Job).limit(1))
    return {"ok": True}


def job_response(job: Job) -> JobResponse:
    return JobResponse(id=job.id, status=job.status, kind=job.kind, credits=job.credits, url=job.url)


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
