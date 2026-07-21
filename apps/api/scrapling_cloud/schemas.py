from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


Format = Literal["markdown", "html", "raw_html", "text", "links", "images", "metadata", "screenshot", "json", "summary"]
Mode = Literal["auto", "static", "dynamic", "stealth"]


class ScrapeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: HttpUrl
    formats: list[Format] = Field(default_factory=lambda: ["markdown"])
    mode: Mode = "auto"
    wait_for: str | None = None
    only_main_content: bool = True
    include_tags: list[str] = Field(default_factory=list, max_length=30)
    exclude_tags: list[str] = Field(default_factory=list, max_length=30)
    headers: dict[str, str] | None = None
    mobile: bool = False
    timeout: int | None = Field(default=None, ge=5, le=300)
    max_age: int = Field(default=0, ge=0, le=7 * 24 * 3600, description="Serve a cached result if newer than this many seconds (0 = always fetch fresh).")
    store_in_cache: bool = True
    screenshot_full_page: bool = False
    proxy: bool = False
    change_tracking: bool = False
    change_tracking_tag: str = Field(default="", max_length=80)
    extraction_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    webhook_url: HttpUrl | None = None


class CrawlRequest(BaseModel):
    url: HttpUrl
    limit: int = Field(default=25, ge=1, le=1000)
    max_depth: int = Field(default=2, ge=0, le=10)
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    formats: list[Format] = Field(default_factory=lambda: ["markdown", "links", "metadata"])
    mode: Mode = "auto"
    only_main_content: bool = True
    allow_subdomains: bool = False
    ignore_query_parameters: bool = False
    respect_robots: bool = True
    delay: float = Field(default=0, ge=0, le=30)
    ai_extract: bool = True
    analysis_prompt: str | None = None
    webhook_url: HttpUrl | None = None


class MapRequest(BaseModel):
    url: HttpUrl
    limit: int = Field(default=250, ge=1, le=5000)
    include_subdomains: bool = False
    sitemap: Literal["include", "skip", "only"] = "include"
    search: str | None = Field(default=None, max_length=200)


class ExtractRequest(BaseModel):
    """Firecrawl-style extraction: send a JSON schema and/or a natural-language prompt.

    Accepts a single `url`, or `urls` with up to 20 entries; entries ending in
    `/*` are expanded via URL discovery (map) before extraction.
    """

    model_config = ConfigDict(populate_by_name=True)

    url: HttpUrl | None = None
    urls: list[str] | None = Field(default=None, max_length=20)
    limit: int = Field(default=10, ge=1, le=20, description="Max pages a wildcard entry expands to.")
    extraction_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    prompt: str | None = Field(default=None, max_length=4000)
    instructions: str | None = Field(default=None, max_length=4000)
    mode: Mode = "auto"
    webhook_url: HttpUrl | None = None

    @model_validator(mode="after")
    def require_inputs(self) -> "ExtractRequest":
        if not self.extraction_schema and not (self.prompt or self.instructions):
            raise ValueError("Provide at least one of 'schema' or 'prompt'.")
        if not self.url and not self.urls:
            raise ValueError("Provide 'url' or 'urls'.")
        for entry in self.urls or []:
            if not entry.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL in 'urls': {entry}")
        return self


class BatchRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=250)
    formats: list[Format] = Field(default_factory=lambda: ["markdown"])
    mode: Mode = "auto"
    max_concurrency: int = Field(default=5, ge=1, le=10)
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
    is_admin: bool = False


class UsageSummary(BaseModel):
    plan: str
    monthly_credits: int
    used_credits: int
    remaining_credits: int
    concurrency_limit: int
    is_admin: bool = False


class DomainProfileResponse(BaseModel):
    domain: str
    preferred_mode: str
    successful_selectors: list[str]
    wait_strategy: dict[str, Any]
    proxy_success_rate: int
    failure_reasons: list[str]
    recommendations: list[str]


class AdminOrganizationResponse(BaseModel):
    id: str
    name: str
    plan: str
    monthly_credits: int
    used_credits: int
    remaining_credits: int
    concurrency_limit: int
    owner_email: str | None = None
    created_at: str


class AdminCreditUpdate(BaseModel):
    operation: Literal["add", "set_monthly", "reset_usage"] = "add"
    credits: int = Field(default=0, ge=0, le=100_000_000)
    plan: str | None = Field(default=None, max_length=40)
    concurrency_limit: int | None = Field(default=None, ge=1, le=1000)


class AdminApiKeyCreate(BaseModel):
    name: str = Field(default="Admin issued key", min_length=1, max_length=160)
    scopes: list[str] = Field(default_factory=lambda: ["scrape", "crawl", "map", "extract"])


NotifyOn = Literal["changed", "meaningful", "always"]


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    url: HttpUrl
    mode: Literal["static", "dynamic", "stealth"] = "static"
    interval_minutes: int = Field(default=60, ge=5, le=10080)
    goal: str | None = Field(default=None, max_length=2000)
    judge_enabled: bool = False
    webhook_url: HttpUrl | None = None
    notify_on: NotifyOn = "changed"
    enabled: bool = True


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    mode: Literal["static", "dynamic", "stealth"] | None = None
    interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    goal: str | None = Field(default=None, max_length=2000)
    judge_enabled: bool | None = None
    webhook_url: HttpUrl | None = None
    notify_on: NotifyOn | None = None
    enabled: bool | None = None


class MonitorResponse(BaseModel):
    id: str
    name: str
    url: str
    mode: str
    interval_minutes: int
    goal: str | None
    judge_enabled: bool
    webhook_url: str | None
    notify_on: str
    enabled: bool
    last_checked_at: str | None
    last_status: str | None
    created_at: str


class MonitorCheckResponse(BaseModel):
    id: str
    change_status: str
    meaningful: bool | None
    reason: str | None
    diff: str | None
    error: str | None
    credits: int
    created_at: str
