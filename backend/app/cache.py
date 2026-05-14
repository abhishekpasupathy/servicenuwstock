import json
import time
from typing import Any

import redis.asyncio as redis

from app.config import get_settings


settings = get_settings()
_redis: redis.Redis | None = None
_memory: dict[str, tuple[float, Any]] = {}


async def get_redis() -> redis.Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
        except Exception:
            _redis = None
    return _redis


async def cache_get(key: str) -> Any | None:
    client = await get_redis()
    if client:
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            pass
    item = _memory.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time.time():
        _memory.pop(key, None)
        return None
    return value


async def cache_set(key: str, value: Any, ttl: int) -> None:
    client = await get_redis()
    if client:
        try:
            await client.setex(key, ttl, json.dumps(value, default=str))
            return
        except Exception:
            pass
    _memory[key] = (time.time() + ttl, value)


async def cache_ping() -> bool:
    return (await get_redis()) is not None
