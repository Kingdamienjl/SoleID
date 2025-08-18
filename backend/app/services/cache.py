from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional

try:
    import redis.asyncio as redis
except Exception:  # noqa: BLE001
    redis = None  # type: ignore


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class InMemoryTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            import time

            now = time.time()
            if entry.expires_at < now:
                self._store.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        import time

        async with self._lock:
            self._store[key] = _CacheEntry(value=value, expires_at=time.time() + ttl_seconds)


_cache_singleton: Any | None = None


def get_cache():
    global _cache_singleton
    if _cache_singleton is not None:
        return _cache_singleton

    redis_url = os.getenv("REDIS_URL")
    if redis_url and redis is not None:
        try:
            _cache_singleton = redis.from_url(redis_url)
            return _cache_singleton
        except Exception:  # noqa: BLE001
            pass

    _cache_singleton = InMemoryTTLCache()
    return _cache_singleton
