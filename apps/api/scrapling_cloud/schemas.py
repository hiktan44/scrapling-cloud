from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


Format = Literal["markdown", "html", "text", "links", "metadata", "screenshot", "json"]
Mode = Literal["auto", "static", "dynamic", "stealth"]


class ScrapeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: HttpUrl
    formats: list[Format] = Field(default_factory=lambda: ["markdown"])
    mode: Mode = "auto"
    wait_for: str | None = None
    only_main_content: bool = True
    extraction_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    webhook_url: HttpUrl | None = None


class CrawlRequest(BaseModel):
    url: HttpUrl
    limit: int = Field(default=25, ge=1, le=1000)
    max_depth: int = Field(default=2, ge=0, le=10)
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    mode: Mode = "auto"
    webhook_url: HttpUrl | None = None


class MapRequest(BaseModel):
    url: HttpUrl
    limit: int = Field(default=250, ge=1, le=5000)
    include_subdomains: bool = False


class ExtractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: HttpUrl
    extraction_schema: dict[str, Any] = Field(alias="schema")
    mode: Mode = "auto"
    instructions: str | None = None
    webhook_url: HttpUrl | None = None


class BatchRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=250)
    formats: list[Format] = Field(default_factory=lambda: ["markdown"])
    mode: Mode = "auto"
    webhook_url: HttpUrl | None = None


class JobResponse(BaseModel):
    id: str
    status: str
    kind: str
    credits: int
    url: str | None = None


class JobDetail(JobResponse):
    request: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    scopes: list[str] = Field(default_factory=lambda: ["scrape", "crawl", "map", "extract"])


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    revoked: bool
    last_used_at: str | None
    created_at: str
    key: str | None = None


class AuthSignup(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    organization_name: str = Field(default="My Workspace", min_length=1, max_length=160)


class AuthLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    api_key: str
    organization_id: str
    organization_name: str
    plan: str
    monthly_credits: int
    concurrency_limit: int


class UsageSummary(BaseModel):
    plan: str
    monthly_credits: int
    used_credits: int
    remaining_credits: int
    concurrency_limit: int


class DomainProfileResponse(BaseModel):
    domain: str
    preferred_mode: str
    successful_selectors: list[str]
    wait_strategy: dict[str, Any]
    proxy_success_rate: int
    failure_reasons: list[str]
    recommendations: list[str]
