import logging
import time

from redis import Redis
from redis.exceptions import RedisError
from rq import Queue

from .config import get_settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis:
    """Shared Redis client with sane timeouts.

    A module-level client keeps the connection pool warm and lets redis-py
    transparently reconnect after transient network hiccups instead of
    failing every other request with a bare 500.
    """
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=5,
            socket_timeout=10,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis


def get_queue() -> Queue:
    return Queue("scrapling-cloud", connection=get_redis(), default_timeout=900)


def enqueue_job(func: str, *args, attempts: int = 4, base_delay: float = 0.4):
    """Enqueue an RQ job with retry/backoff.

    Transient Redis errors (connection resets, brief restarts) should not
    surface to API callers as HTTP 500 after the job row was committed.
    """
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return get_queue().enqueue(func, *args)
        except RedisError as exc:
            last_error = exc
            logger.warning("enqueue attempt %s/%s failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(base_delay * (2 ** (attempt - 1)))
    raise last_error  # type: ignore[misc]
