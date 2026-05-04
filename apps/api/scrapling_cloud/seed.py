from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import ApiKey, Organization, User
from .security import hash_api_key, hash_password


def seed_demo(db: Session) -> None:
    settings = get_settings()
    demo_email = "demo@scrapling.cloud"
    existing_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(settings.demo_api_key)))
    existing_user = db.scalar(select(User).where(User.email == demo_email))
    if existing_key is not None:
        if existing_user is not None and existing_user.password_hash is None:
            existing_user.password_hash = hash_password("demo12345")
            db.commit()
        return

    org = Organization(name="Demo Workspace", plan="growth", monthly_credits=50000, concurrency_limit=8)
    db.add(org)
    db.flush()
    db.add(User(organization_id=org.id, email=demo_email, password_hash=hash_password("demo12345"), role="owner"))
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
