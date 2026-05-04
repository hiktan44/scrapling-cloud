from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return uuid4().hex


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class JobKind(str, Enum):
    scrape = "scrape"
    crawl = "crawl"
    map = "map"
    extract = "extract"
    batch = "batch"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="starter")
    monthly_credits: Mapped[int] = mapped_column(Integer, default=10000)
    used_credits: Mapped[int] = mapped_column(Integer, default=0)
    concurrency_limit: Mapped[int] = mapped_column(Integer, default=3)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="organization")
    jobs: Mapped[list["Job"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="api_keys")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=JobStatus.queued.value)
    url: Mapped[str | None] = mapped_column(Text)
    request: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    webhook_url: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="jobs")
    events: Mapped[list["JobEvent"]] = relationship(back_populates="job")


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped[Job] = relationship(back_populates="events")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"))
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DomainProfile(Base):
    __tablename__ = "domain_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "domain", name="uq_domain_profile"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_mode: Mapped[str] = mapped_column(String(40), default="static")
    successful_selectors: Mapped[list[str]] = mapped_column(JSON, default=list)
    wait_strategy: Mapped[dict] = mapped_column(JSON, default=dict)
    proxy_success_rate: Mapped[int] = mapped_column(Integer, default=0)
    failure_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
