from redis import Redis
from rq import Queue

from .config import get_settings


def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def get_queue() -> Queue:
    return Queue("scrapling-cloud", connection=get_redis(), default_timeout=600)
