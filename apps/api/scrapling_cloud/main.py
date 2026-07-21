import json
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from redis.exceptions import RedisError
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import __version__
from .billing import estimate_credits
from .config import get_settings
from .db import create_all, get_db
from .intel import build_export_xlsx, parse_urls
from .parse import parse_file
from .jobs import create_job, requeue_stuck_jobs, webhook_secret_for
from .models import ApiKey, DomainProfile, Job, JobEvent, JobKind, JobStatus, Monitor, MonitorCheck, Organization, UsageEvent, User
from .monitors import run_monitor_check
from .queue import get_redis
from .ratelimit import client_ip, rate_limit
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
    MonitorCheckResponse,
    MonitorCreate,
    CheckoutRequest,
    MonitorResponse,
    MonitorUpdate,
    PortalRequest,
    ScrapeRequest,
    SearchRequest,
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


@app.get("/v1/public/stats")
def public_stats(db: Session = Depends(get_db)) -> dict:
    """Live platform metrics for the landing page (no auth, cached 60s)."""
    cache_key = "public:stats"
    try:
        cached = get_redis().get(cache_key)
        if cached:
            return json.loads(cached)
    except RedisError:
        pass

    since = datetime.utcnow() - timedelta(days=7)
    succeeded = db.scalar(
        select(func.count(Job.id)).where(Job.status == JobStatus.succeeded.value, Job.created_at >= since)
    ) or 0
    failed = db.scalar(
        select(func.count(Job.id)).where(Job.status == JobStatus.failed.value, Job.created_at >= since)
    ) or 0
    finished = succeeded + failed
    payload = {
        "success_rate": round(succeeded / finished * 100, 1) if finished else None,
        "succeeded": succeeded,
        "failed": failed,
        "jobs_total": finished,
        "window_days": 7,
    }
    try:
        get_redis().setex(cache_key, 60, json.dumps(payload))
    except RedisError:
        pass
    return payload


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
def signup(payload: AuthSignup, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    rate_limit(f"signup:{client_ip(request)}", limit=5, window_seconds=60)
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
def login(payload: AuthLogin, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    rate_limit(f"login:{client_ip(request)}", limit=10, window_seconds=60)
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
    # Revoke previous dashboard session keys: every login mints a fresh key,
    # and without cleanup the key list would grow unbounded (and stay valid).
    stale_keys = db.scalars(
        select(ApiKey).where(
            ApiKey.organization_id == organization.id,
            ApiKey.name == "Dashboard session",
            ApiKey.revoked.is_(False),
        )
    ).all()
    for stale in stale_keys:
        stale.revoked = True
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


@app.post("/v1/search")
async def search_endpoint(
    payload: SearchRequest,
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict:
    from .search import SearchUnavailable, search_and_scrape

    # 2 credits per 10 results, +1 per scraped result page.
    scrape_formats = payload.scrape_formats or []
    credits = max(2, 2 * ((payload.limit + 9) // 10)) + (payload.limit if scrape_formats else 0)
    from .billing import reserve_credits

    reserve_credits(db, principal.organization, credits, None, "search_sync")
    db.commit()
    try:
        result = await search_and_scrape(
            payload.query,
            payload.limit,
            scrape_formats or None,
            payload.categories,
            payload.language,
            payload.time_range,
            payload.mode,
        )
    except SearchUnavailable as exc:
        from .jobs import refund_credits

        refund_credits(db, principal.organization, credits, None, "search_unavailable_refund")
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        from .jobs import refund_credits

        refund_credits(db, principal.organization, credits, None, "search_failed_refund")
        db.commit()
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc
    result["credits"] = credits
    return result


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


INTEL_MAX_BYTES = 25 * 1024 * 1024


@app.post("/v1/parse")
async def parse_endpoint(
    file: UploadFile = File(...),
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict:
    """Parse an uploaded document (PDF/DOCX/XLSX/HTML/TXT/CSV/MD) into markdown."""
    data = await file.read()
    if len(data) > INTEL_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 25MB limit.")
    try:
        parsed = await run_in_threadpool(parse_file, file.filename or "upload", data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"File could not be parsed: {exc}") from exc

    from .billing import reserve_credits

    credits = 1 + (parsed.get("pages") or 0) // 10
    reserve_credits(db, principal.organization, credits, None, "parse_sync")
    db.commit()
    parsed["credits"] = credits
    return parsed


@app.post("/v1/intel/upload")
async def intel_upload(
    file: UploadFile = File(...),
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict:
    """Excel/CSV/TXT dosyasından site listesi alıp toplu analiz job'u başlat."""
    rate_limit(f"intel:{principal.organization.id}", limit=10, window_seconds=60)
    content = await file.read(INTEL_MAX_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Dosya boş")
    if len(content) > INTEL_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Dosya çok büyük (maksimum 25 MB)")
    try:
        urls = parse_urls(file.filename or "liste.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    if not urls:
        raise HTTPException(
            status_code=422,
            detail="Dosyada geçerli site adresi bulunamadı. Her satıra bir adres (örn. firma.com veya https://firma.com) ekleyin.",
        )
    job = create_job(db, principal.organization, JobKind.intel, {"urls": urls})
    return {"job_id": job.id, "url_count": len(urls), "status": job.status, "credits": job.credits}


@app.get("/v1/intel/{job_id}/export")
def intel_export(job_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> Response:
    """Tamamlanan toplu analiz job'unun Excel çıktısını indir."""
    job = db.get(Job, job_id)
    if job is None or job.organization_id != principal.organization.id or job.kind != JobKind.intel.value:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.succeeded.value:
        raise HTTPException(status_code=409, detail=f"Analiz henüz tamamlanmadı (durum: {job.status})")
    data = build_export_xlsx((job.result or {}).get("items") or [])
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="firma-analiz-sonuclari.xlsx"'},
    )


@app.post("/v1/playground/scrape")
async def playground_scrape(payload: ScrapeRequest, request: Request) -> dict:
    rate_limit(f"playground:{client_ip(request)}", limit=30, window_seconds=60)
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


SSE_MAX_SECONDS = 600
SSE_POLL_SECONDS = 2


@app.get("/v1/jobs/{job_id}/events")
def job_events(job_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> StreamingResponse:
    job = db.get(Job, job_id)
    if job is None or job.organization_id != principal.organization.id:
        raise HTTPException(status_code=404, detail="Job not found")

    def event_stream():
        import time as _time

        from .db import SessionLocal

        sent: set[str] = set()
        deadline = _time.time() + SSE_MAX_SECONDS
        while _time.time() < deadline:
            session = SessionLocal()
            try:
                events = session.scalars(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at)).all()
                for event in events:
                    if event.id in sent:
                        continue
                    sent.add(event.id)
                    payload = json.dumps(
                        {"level": event.level, "message": event.message, "data": event.data, "at": event.created_at.isoformat()},
                        ensure_ascii=False,
                        default=str,
                    )
                    yield f"event: {event.level}\ndata: {payload}\n\n"
                current = session.get(Job, job_id)
                if current is None or current.status in (JobStatus.succeeded.value, JobStatus.failed.value, JobStatus.canceled.value):
                    yield f"event: done\ndata: {json.dumps({'status': current.status if current else 'unknown'})}\n\n"
                    return
            finally:
                session.close()
            _time.sleep(SSE_POLL_SECONDS)
        yield f"event: timeout\ndata: {json.dumps({'status': 'still-running'})}\n\n"

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


MAX_MONITORS_PER_ORG = 20


def monitor_response(monitor: Monitor) -> MonitorResponse:
    return MonitorResponse(
        id=monitor.id,
        name=monitor.name,
        url=monitor.url,
        mode=monitor.mode,
        interval_minutes=monitor.interval_minutes,
        goal=monitor.goal,
        judge_enabled=monitor.judge_enabled,
        webhook_url=monitor.webhook_url,
        notify_on=monitor.notify_on,
        enabled=monitor.enabled,
        last_checked_at=monitor.last_checked_at.isoformat() if monitor.last_checked_at else None,
        last_status=monitor.last_status,
        created_at=monitor.created_at.isoformat(),
    )


def check_response(check: MonitorCheck) -> MonitorCheckResponse:
    return MonitorCheckResponse(
        id=check.id,
        change_status=check.change_status,
        meaningful=check.meaningful,
        reason=check.reason,
        diff=check.diff,
        error=check.error,
        credits=check.credits,
        created_at=check.created_at.isoformat(),
    )


def get_org_monitor(db: Session, principal: Principal, monitor_id: str) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None or monitor.organization_id != principal.organization.id:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@app.post("/v1/monitors", response_model=MonitorResponse)
def create_monitor(payload: MonitorCreate, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> MonitorResponse:
    count = db.scalar(select(func.count()).select_from(Monitor).where(Monitor.organization_id == principal.organization.id))
    if count is not None and count >= MAX_MONITORS_PER_ORG:
        raise HTTPException(status_code=422, detail=f"Monitor limit reached ({MAX_MONITORS_PER_ORG}).")
    monitor = Monitor(
        organization_id=principal.organization.id,
        name=payload.name,
        url=str(payload.url),
        mode=payload.mode,
        interval_minutes=payload.interval_minutes,
        goal=payload.goal,
        judge_enabled=payload.judge_enabled,
        webhook_url=str(payload.webhook_url) if payload.webhook_url else None,
        notify_on=payload.notify_on,
        enabled=payload.enabled,
    )
    db.add(monitor)
    db.commit()
    return monitor_response(monitor)


@app.get("/v1/monitors", response_model=list[MonitorResponse])
def list_monitors(principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> list[MonitorResponse]:
    monitors = db.scalars(
        select(Monitor).where(Monitor.organization_id == principal.organization.id).order_by(desc(Monitor.created_at))
    ).all()
    return [monitor_response(monitor) for monitor in monitors]


@app.get("/v1/monitors/{monitor_id}")
def get_monitor(monitor_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    monitor = get_org_monitor(db, principal, monitor_id)
    checks = db.scalars(
        select(MonitorCheck).where(MonitorCheck.monitor_id == monitor.id).order_by(desc(MonitorCheck.created_at)).limit(20)
    ).all()
    return {"monitor": monitor_response(monitor).model_dump(), "checks": [check_response(check).model_dump() for check in checks]}


@app.patch("/v1/monitors/{monitor_id}", response_model=MonitorResponse)
def update_monitor(
    monitor_id: str,
    payload: MonitorUpdate,
    principal: Principal = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> MonitorResponse:
    monitor = get_org_monitor(db, principal, monitor_id)
    updates = payload.model_dump(exclude_unset=True)
    if "webhook_url" in updates and updates["webhook_url"] is not None:
        updates["webhook_url"] = str(updates["webhook_url"])
    for field, value in updates.items():
        setattr(monitor, field, value)
    db.commit()
    return monitor_response(monitor)


@app.delete("/v1/monitors/{monitor_id}")
def delete_monitor(monitor_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    from sqlalchemy import delete as sa_delete

    from .models import PageSnapshot

    monitor = get_org_monitor(db, principal, monitor_id)
    # Bulk-delete children first so the FK to monitors is clear before the
    # parent row is removed. There is no ORM relationship declaring this
    # dependency, so SQLAlchemy would otherwise emit the DELETEs in an order
    # Postgres rejects (FK violation). Also drop the monitor's page snapshots.
    db.execute(sa_delete(MonitorCheck).where(MonitorCheck.monitor_id == monitor.id))
    db.execute(sa_delete(PageSnapshot).where(PageSnapshot.tag == f"monitor:{monitor.id}"))
    db.delete(monitor)
    db.commit()
    return {"deleted": monitor_id}


@app.post("/v1/monitors/{monitor_id}/run", response_model=MonitorCheckResponse)
async def run_monitor_now(monitor_id: str, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> MonitorCheckResponse:
    monitor = get_org_monitor(db, principal, monitor_id)
    check = await run_monitor_check(db, monitor)
    return check_response(check)


@app.get("/v1/webhook-secret")
def webhook_secret(principal: Principal = Depends(require_api_key)) -> dict:
    """Return the signing secret used for X-Scrapling-Signature webhook headers."""
    return {
        "secret": webhook_secret_for(principal.organization.id),
        "header": "X-Scrapling-Signature",
        "algorithm": "hmac-sha256",
    }


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


@app.post("/v1/admin/requeue")
def admin_requeue(
    _admin: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Re-enqueue jobs stuck in 'queued' state (e.g. after a Redis outage)."""
    requeued = requeue_stuck_jobs(db, older_than_seconds=0)
    return {"requeued": requeued}


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


@app.get("/v1/billing/plans")
def billing_plans() -> dict:
    from .plans import PLANS

    return {
        "plans": [
            {
                "key": p.key,
                "name": p.name,
                "monthly_credits": p.monthly_credits,
                "concurrency_limit": p.concurrency_limit,
                "monthly_price_usd": p.monthly_price_usd,
            }
            for p in PLANS.values()
        ]
    }


@app.post("/v1/billing/checkout")
def billing_checkout(payload: CheckoutRequest, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    from .billing_stripe import StripeNotConfigured, create_checkout_session

    try:
        url = create_checkout_session(db, principal.organization, payload.plan, str(payload.success_url), str(payload.cancel_url))
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"checkout_url": url}


@app.post("/v1/billing/portal")
def billing_portal(payload: PortalRequest, principal: Principal = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    from .billing_stripe import StripeNotConfigured, create_portal_session

    try:
        url = create_portal_session(principal.organization, str(payload.return_url))
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"portal_url": url}


@app.post("/v1/billing/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    from .billing_stripe import StripeNotConfigured, handle_event, verify_and_parse_event

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = verify_and_parse_event(payload, signature)
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Signature mismatch or malformed body - reject so Stripe retries.
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc
    result = handle_event(db, event)
    return {"received": True, "result": result}
