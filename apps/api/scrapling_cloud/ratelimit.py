import logging

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from .queue import get_redis

logger = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    """Best-effort client IP behind a reverse proxy (Traefik/Coolify)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(key: str, limit: int, window_seconds: int = 60) -> None:
    """Fixed-window rate limiter backed by Redis.

    Fails open when Redis is unavailable so a cache outage never takes the
    API down with it.
    """
    try:
        redis = get_redis()
        bucket = f"rl:{key}"
        count = redis.incr(bucket)
        if count == 1:
            redis.expire(bucket, window_seconds)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down and retry shortly.",
            )
    except RedisError as exc:
        logger.warning("rate limiter unavailable, allowing request: %s", exc)
