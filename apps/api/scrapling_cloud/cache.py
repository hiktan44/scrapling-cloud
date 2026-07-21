"""Best-effort Redis cache for scrape results (Firecrawl maxAge parity).

Callers opt in per request with `max_age` (seconds). Fresh results are
stored for CACHE_TTL_SECONDS unless `store_in_cache` is false. Redis being
unavailable never breaks a scrape - every operation swallows errors.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time

from .queue import get_redis

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 2 * 24 * 3600
_CACHE_KEY_FIELDS = (
    "url",
    "mode",
    "formats",
    "only_main_content",
    "include_tags",
    "exclude_tags",
    "wait_for",
    "schema",
    "screenshot_full_page",
    "mobile",
    "headers",
)


def cache_key(payload: dict) -> str:
    relevant = {}
    for field in _CACHE_KEY_FIELDS:
        value = payload.get(field)
        if isinstance(value, list):
            value = sorted(str(item) for item in value)
        relevant[field] = value
    digest = hashlib.sha256(json.dumps(relevant, sort_keys=True, default=str).encode()).hexdigest()
    return f"scrape-cache:{digest}"


def cache_get(payload: dict) -> dict | None:
    max_age = int(payload.get("max_age") or 0)
    if max_age <= 0:
        return None
    try:
        raw = get_redis().get(cache_key(payload))
        if not raw:
            return None
        entry = json.loads(raw)
        age = time.time() - float(entry.get("cached_at_ts", 0))
        if age > max_age:
            return None
        result = entry.get("result") or {}
        result["cached"] = True
        result["cache_age_seconds"] = int(age)
        return result
    except Exception as exc:
        logger.debug("scrape cache read skipped: %s", exc)
        return None


def cache_set(payload: dict, result: dict) -> None:
    if payload.get("store_in_cache") is False:
        return
    try:
        entry = json.dumps({"cached_at_ts": time.time(), "result": result}, default=str)
        get_redis().setex(cache_key(payload), CACHE_TTL_SECONDS, entry)
    except Exception as exc:
        logger.debug("scrape cache write skipped: %s", exc)
