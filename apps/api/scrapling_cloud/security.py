import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import ApiKey, Organization

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_api_key() -> str:
    return f"sk_{secrets.token_urlsafe(32)}"


@dataclass
class Principal:
    organization: Organization
    api_key: ApiKey


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer API key")

    token = credentials.credentials
    key_hash = hash_api_key(token)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked.is_(False)))
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    organization = db.get(Organization, api_key.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid organization")

    api_key.last_used_at = datetime.utcnow()
    db.commit()
    return Principal(organization=organization, api_key=api_key)
