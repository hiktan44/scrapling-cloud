from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import ApiKey, Organization, User
from .security import hash_api_key


def seed_demo(db: Session) -> None:
    settings = get_settings()
    existing = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(settings.demo_api_key)))
    if existing is not None:
        return

    org = Organization(name="Demo Workspace", plan="growth", monthly_credits=50000, concurrency_limit=8)
    db.add(org)
    db.flush()
    db.add(User(organization_id=org.id, email="demo@scrapling.cloud", role="owner"))
    db.add(
        ApiKey(
            organization_id=org.id,
            name="Demo Local Key",
            key_prefix=settings.demo_api_key[:10],
            key_hash=hash_api_key(settings.demo_api_key),
            scopes=["scrape", "crawl", "map", "extract"],
        )
    )
    db.commit()
