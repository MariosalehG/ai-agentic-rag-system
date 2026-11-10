"""Redis caching with graceful degradation.

A cache outage must never take down answering. Every operation is wrapped so
a Redis failure logs and returns None rather than propagating — the pipeline
then just does the work it would have done anyway.
"""

import hashlib
import json
from typing import Any

import redis

from src.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.from_url(get_settings().redis_url, decode_responses=True)
            _client.ping()
        except Exception as exc:
            print(f"Redis unavailable, caching disabled: {exc}")
            return None
    return _client


def make_key(prefix: str, payload: dict[str, Any]) -> str:
    """Build a deterministic cache key from a payload.

    sort_keys ensures {"a":1,"b":2} and {"b":2,"a":1} hash identically —
    without it, equivalent requests would miss the cache.
    """
    raw = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"{prefix}:{digest}"


def cache_get(key: str) -> Any | None:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        print(f"Cache read failed: {exc}")
        return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        print(f"Cache write failed: {exc}")


def cache_clear(prefix: str) -> int:
    """Delete all keys under a prefix. Use after re-indexing or prompt changes."""
    client = get_redis()
    if client is None:
        return 0
    try:
        keys = list(client.scan_iter(f"{prefix}:*"))
        return client.delete(*keys) if keys else 0
    except Exception as exc:
        print(f"Cache clear failed: {exc}")
        return 0