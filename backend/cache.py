"""任务缓存。线上使用华为云 Redis，本地无 Redis 时自动降级到进程内内存。"""

from __future__ import annotations

import json
import time
from typing import Any

from backend.config import get_settings


class MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        expire_at, value = item
        if expire_at and expire_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        expire_at = time.time() + ttl if ttl else 0.0
        self._store[key] = (expire_at, value)


class RedisCache:
    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._client.set(key, value, ex=ttl)


class Cache:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.redis_url:
            try:
                self._backend: MemoryCache | RedisCache = RedisCache(settings.redis_url)
            except Exception:
                self._backend = MemoryCache()
        else:
            self._backend = MemoryCache()

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self._backend.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, payload: dict[str, Any], ttl: int = 3600) -> None:
        self._backend.set(key, json.dumps(payload, ensure_ascii=False), ttl)


cache = Cache()
