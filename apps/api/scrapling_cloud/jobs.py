from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from .billing import estimate_credits, reserve_credits
from .learning import apply_profile_defaults
from .models import Job, JobEvent, JobKind, JobStatus, Organization
from .queue import get_queue


def create_job(db: Session, organization: Organization, kind: JobKind, payload: dict) -> Job:
    enriched = apply_profile_defaults(db, organization.id, payload)
    credits = estimate_credits(kind.value, enriched)
    job = Job(
        organization_id=organization.id,
        kind=kind.value,
        status=JobStatus.queued.value,
        url=str(enriched.get("url") or ""),
        request=enriched,
        credits=credits,
        webhook_url=str(enriched.get("webhook_url")) if enriched.get("webhook_url") else None,
    )
    db.add(job)
    db.flush()
    reserve_credits(db, organization, credits, job.id, f"{kind.value}_job")
    db.add(JobEvent(job_id=job.id, message="Job queued", data={"credits": credits}))
    db.commit()
    get_queue().enqueue("scrapling_cloud.worker.run_job", job.id)
    return job


async def send_webhook(job: Job) -> None:
    if not job.webhook_url:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            job.webhook_url,
            json={"id": job.id, "status": job.status, "kind": job.kind, "result": job.result, "error": job.error},
        )


def mark_running(db: Session, job: Job) -> None:
    job.status = JobStatus.running.value
    job.started_at = datetime.utcnow()
    db.add(JobEvent(job_id=job.id, message="Job started"))
    db.commit()


def mark_succeeded(db: Session, job: Job, result: dict) -> None:
    job.status = JobStatus.succeeded.value
    job.result = result
    job.finished_at = datetime.utcnow()
    db.add(JobEvent(job_id=job.id, message="Job succeeded"))
    db.commit()


def mark_failed(db: Session, job: Job, error: str, reason: str) -> None:
    job.status = JobStatus.failed.value
    job.error = error
    job.finished_at = datetime.utcnow()
    db.add(JobEvent(job_id=job.id, level="error", message="Job failed", data={"reason": reason}))
    db.commit()
