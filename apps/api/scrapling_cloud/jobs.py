import logging
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .billing import estimate_credits, reserve_credits
from .learning import apply_profile_defaults
from .models import Job, JobEvent, JobKind, JobStatus, Organization, UsageEvent
from .queue import enqueue_job

logger = logging.getLogger(__name__)


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

    try:
        enqueue_job("scrapling_cloud.worker.run_job", job.id)
    except Exception as exc:
        # The job row is already committed but never reached the worker queue.
        # Mark it failed and refund the reserved credits so users are never
        # charged for work that will not run, then surface a retryable 503.
        logger.error("enqueue failed for job %s: %s", job.id, exc)
        refund_credits(db, organization, credits, job.id, f"{kind.value}_queue_unavailable_refund")
        job.status = JobStatus.failed.value
        job.error = f"Job could not be queued: {exc}"
        job.finished_at = datetime.utcnow()
        db.add(JobEvent(job_id=job.id, level="error", message="Job failed to reach the queue; reserved credits refunded"))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job queue is temporarily unavailable. Please retry in a few seconds - no credits were charged.",
        ) from exc
    return job


def refund_credits(db: Session, organization: Organization, credits: int, job_id: str | None, reason: str) -> None:
    organization.used_credits = max(0, organization.used_credits - credits)
    db.add(UsageEvent(organization_id=organization.id, job_id=job_id, credits=-credits, reason=reason))


def requeue_stuck_jobs(db: Session, older_than_seconds: int = 90, limit: int = 200, cooldown_seconds: int = 300) -> int:
    """Re-enqueue jobs that sit in 'queued' state but never reached Redis.

    This recovers jobs orphaned by transient enqueue failures or worker
    restarts. Delivery is idempotent: the worker skips jobs that are no
    longer in 'queued' status, and a per-job cooldown keeps repeated sweeps
    from piling duplicate entries into the queue.
    """
    cutoff = datetime.utcnow() - timedelta(seconds=older_than_seconds)
    cooldown = datetime.utcnow() - timedelta(seconds=cooldown_seconds)
    jobs = db.scalars(
        select(Job)
        .where(Job.status == JobStatus.queued.value, Job.created_at < cutoff)
        .order_by(Job.created_at)
        .limit(limit)
    ).all()
    requeued = 0
    for job in jobs:
        last_sweep = db.scalar(
            select(JobEvent)
            .where(JobEvent.job_id == job.id, JobEvent.message == "Job re-queued by recovery sweep")
            .order_by(desc(JobEvent.created_at))
            .limit(1)
        )
        if last_sweep is not None and last_sweep.created_at > cooldown:
            continue
        try:
            enqueue_job("scrapling_cloud.worker.run_job", job.id, attempts=2)
        except Exception as exc:
            logger.warning("requeue sweep stopped, queue still unavailable: %s", exc)
            break
        db.add(JobEvent(job_id=job.id, message="Job re-queued by recovery sweep"))
        requeued += 1
    if requeued:
        db.commit()
        logger.info("requeue sweep re-enqueued %s stuck job(s)", requeued)
    return requeued


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
