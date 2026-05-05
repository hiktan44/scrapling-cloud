from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import JobKind, Organization, UsageEvent


BASE_CREDITS = {
    JobKind.scrape.value: 1,
    JobKind.map.value: 2,
    JobKind.extract.value: 4,
    JobKind.crawl.value: 5,
    JobKind.batch.value: 1,
}


def estimate_credits(kind: str, payload: dict) -> int:
    credits = BASE_CREDITS.get(kind, 1)
    mode = payload.get("mode")
    formats = payload.get("formats") or []
    if mode == "dynamic":
        credits += 4
    if mode == "stealth":
        credits += 8
    if "screenshot" in formats:
        credits += 3
    if payload.get("schema"):
        credits += 3
    if payload.get("ai_extract"):
        credits += 3
    if kind == JobKind.crawl.value:
        credits += max(1, int(payload.get("limit", 25)) // 10)
    if kind == JobKind.batch.value:
        credits *= len(payload.get("urls", []))
    return max(1, credits)


def reserve_credits(db: Session, organization: Organization, credits: int, job_id: str | None, reason: str) -> None:
    remaining = organization.monthly_credits - organization.used_credits
    if credits > remaining:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient monthly credits. Upgrade your plan or wait for renewal.",
        )
    organization.used_credits += credits
    db.add(UsageEvent(organization_id=organization.id, job_id=job_id, credits=credits, reason=reason))
