"""Redis-backed JSON cache with graceful degradation when Redis is down."""

import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    """Return a lazily created singleton Redis client."""
    global _client
    if _client is None:
        _client = redis.from_url(_settings.redis_url, decode_responses=True)
    return _client


async def close_client() -> None:
    """Close the Redis client if it was created."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def ping() -> bool:
    """Return True if Redis responds to a ping."""
    try:
        return bool(await get_client().ping())
    except Exception:  # noqa: BLE001
        return False


async def get_json(key: str) -> Any | None:
    """Return the decoded JSON value for ``key`` or ``None`` (no-op on failure)."""
    try:
        raw = await get_client().get(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis get failed for %s: %s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_json(key: str, value: Any, ttl: int) -> None:
    """Store ``value`` as JSON under ``key`` with a TTL (no-op on failure)."""
    try:
        await get_client().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis set failed for %s: %s", key, exc)
