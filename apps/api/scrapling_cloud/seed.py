import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import ApiKey, Organization, User
from .security import hash_api_key, hash_password, verify_password

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@scrapling.cloud"
DEFAULT_DEMO_KEY = "sk_demo_local_development_key"
DEFAULT_ADMIN_KEY = "sk_admin_local_development_key"


def seed_demo(db: Session) -> None:
    settings = get_settings()
    if not settings.seed_demo:
        _disable_demo(db)
        return

    demo_key_hash = hash_api_key(settings.demo_api_key)
    existing_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == demo_key_hash, ApiKey.revoked.is_(False)))
    existing_user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing_key is not None:
        if existing_user is not None and existing_user.password_hash is None:
            existing_user.password_hash = hash_password(settings.demo_password)
            db.commit()
        return

    org = None
    if existing_user is not None:
        org = db.get(Organization, existing_user.organization_id)
    if org is None:
        org = Organization(name="Demo Workspace", plan="growth", monthly_credits=50000, concurrency_limit=8)
        db.add(org)
        db.flush()
    if existing_user is None:
        db.add(User(organization_id=org.id, email=DEMO_EMAIL, password_hash=hash_password(settings.demo_password), role="owner"))
    elif existing_user.password_hash is None:
        existing_user.password_hash = hash_password(settings.demo_password)
    db.add(
        ApiKey(
            organization_id=org.id,
            name="Demo Local Key",
            key_prefix=settings.demo_api_key[:10],
            key_hash=demo_key_hash,
            scopes=["scrape", "crawl", "map", "extract"],
        )
    )
    db.commit()


def _disable_demo(db: Session) -> None:
    """Lock the shared demo account.

    The demo credentials were publicly visible (login page + repository),
    so anyone could log in and burn the demo workspace's credits. When
    SEED_DEMO is off, the demo user is locked and every API key of the demo
    workspace is revoked. Re-enable anytime with SEED_DEMO=true and a
    private DEMO_PASSWORD.
    """
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        return
    changed = False
    if user.password_hash is not None:
        user.password_hash = None
        changed = True
    keys = db.scalars(
        select(ApiKey).where(ApiKey.organization_id == user.organization_id, ApiKey.revoked.is_(False))
    ).all()
    for key in keys:
        key.revoked = True
        changed = True
    if changed:
        db.commit()
        logger.info("demo account locked and its API keys revoked (SEED_DEMO is off)")


def seed_admin(db: Session) -> None:
    settings = get_settings()
    email = settings.admin_email.strip().lower()
    production = settings.is_production
    weak_password = settings.admin_password in {"", "admin12345"}
    weak_key = settings.admin_api_key in {"", DEFAULT_ADMIN_KEY}

    existing_user = db.scalar(select(User).where(User.email == email))

    if existing_user is None:
        if production and weak_password:
            logger.critical("ADMIN_PASSWORD is not set - skipping admin seed in production")
            return
        org = Organization(name="Admin Workspace", plan="admin", monthly_credits=1_000_000, concurrency_limit=50)
        db.add(org)
        db.flush()
        existing_user = User(organization_id=org.id, email=email, password_hash=hash_password(settings.admin_password or "admin12345"), role="admin")
        db.add(existing_user)
    else:
        existing_user.role = "admin"
        if production and existing_user.password_hash and verify_password("admin12345", existing_user.password_hash):
            # The default admin password was public in the repository - lock
            # the account until a private ADMIN_PASSWORD is provided.
            existing_user.password_hash = None
            logger.critical("admin account locked: default ADMIN_PASSWORD detected in production - set ADMIN_PASSWORD to re-enable")
        if existing_user.password_hash is None and not (production and weak_password):
            existing_user.password_hash = hash_password(settings.admin_password or "admin12345")
        org = db.get(Organization, existing_user.organization_id)
        if org is not None:
            org.plan = "admin"
            org.monthly_credits = max(org.monthly_credits, 1_000_000)
            org.concurrency_limit = max(org.concurrency_limit, 50)

    if production and weak_key:
        # The well-known development admin key must never work in production.
        known = db.scalar(
            select(ApiKey).where(ApiKey.key_hash == hash_api_key(DEFAULT_ADMIN_KEY), ApiKey.revoked.is_(False))
        )
        if known is not None:
            known.revoked = True
            logger.critical("default development admin API key revoked in production")
        db.commit()
        return

    if weak_key:
        db.commit()
        return

    existing_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(settings.admin_api_key)))
    if existing_key is None:
        db.add(
            ApiKey(
                organization_id=existing_user.organization_id,
                name="Admin Root Key",
                key_prefix=settings.admin_api_key[:10],
                key_hash=hash_api_key(settings.admin_api_key),
                scopes=["admin", "scrape", "crawl", "map", "extract"],
            )
        )
    elif "admin" not in (existing_key.scopes or []):
        existing_key.scopes = sorted(set((existing_key.scopes or []) + ["admin", "scrape", "crawl", "map", "extract"]))

    db.commit()
