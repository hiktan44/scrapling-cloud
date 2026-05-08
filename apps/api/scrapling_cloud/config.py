from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Scrapling Cloud"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./scrapling_cloud.sqlite3"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    encryption_key: str = "change-me"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    llm_provider: str = "zai"
    z_ai_api_key: str | None = None
    zai_api_key: str | None = None
    zai_base_url: str = "https://api.z.ai/api/paas/v4"
    zai_model: str = "glm-5.1"
    proxy_provider_url: str | None = None
    proxy_provider_token: str | None = None
    demo_api_key: str = Field(default="sk_demo_local_development_key")
    admin_email: str = "admin@scrapling.cloud"
    admin_password: str = "admin12345"
    admin_api_key: str = Field(default="sk_admin_local_development_key")
    allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
