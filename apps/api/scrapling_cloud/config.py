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
    proxy_provider_url: str | None = None
    proxy_provider_token: str | None = None
    demo_api_key: str = Field(default="sk_demo_local_development_key")
    allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
