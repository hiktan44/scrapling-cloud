from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DomainProfile


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def get_or_create_profile(db: Session, organization_id: str, url: str) -> DomainProfile:
    domain = domain_from_url(url)
    profile = db.scalar(
        select(DomainProfile).where(
            DomainProfile.organization_id == organization_id,
            DomainProfile.domain == domain,
        )
    )
    if profile is None:
        profile = DomainProfile(organization_id=organization_id, domain=domain)
        db.add(profile)
        db.flush()
    return profile


def apply_profile_defaults(db: Session, organization_id: str, payload: dict) -> dict:
    url = str(payload.get("url") or "")
    if not url:
        return payload
    profile = get_or_create_profile(db, organization_id, url)
    enriched = dict(payload)
    if enriched.get("mode") == "auto":
        enriched["mode"] = profile.preferred_mode
    if not enriched.get("wait_for") and profile.wait_strategy.get("selector"):
        enriched["wait_for"] = profile.wait_strategy["selector"]
    return enriched


def record_success(db: Session, organization_id: str, url: str, mode: str, selectors: list[str] | None = None) -> None:
    profile = get_or_create_profile(db, organization_id, url)
    profile.preferred_mode = mode if mode != "auto" else profile.preferred_mode
    if selectors:
        merged = list(dict.fromkeys([*profile.successful_selectors, *selectors]))
        profile.successful_selectors = merged[:20]
    profile.recommendations = [item for item in profile.recommendations if "failed" not in item.lower()]


def record_failure(db: Session, organization_id: str, url: str, reason: str) -> None:
    profile = get_or_create_profile(db, organization_id, url)
    profile.failure_reasons = list(dict.fromkeys([*profile.failure_reasons, reason]))[:20]
    recommendations = set(profile.recommendations)
    if reason in {"timeout", "empty-content", "selector-miss"}:
        recommendations.add("Try dynamic mode or add a wait selector for this domain.")
    if reason in {"blocked", "captcha"}:
        recommendations.add("Enable stealth mode and configure a proxy provider for this domain.")
    profile.recommendations = sorted(recommendations)
