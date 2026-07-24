"""基于内存的异步 TTL + LRU 缓存。"""
import time
import asyncio
from collections import OrderedDict
from typing import Any, Optional, Callable, Dict

from .config import settings


class AsyncTTLCache:
    """异步安全的 TTL + LRU 缓存实现。"""

    def __init__(self, max_size: int = 500, default_ttl: int = 300):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, tuple] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expire_at = self._store[key]
            if time.time() > expire_at:
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._lock:
            expire_at = time.time() + (ttl if ttl is not None else self._default_ttl)
            if key in self._store:
                del self._store[key]
            self._store[key] = (value, expire_at)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    async def get_or_set(self, key: str, factory: Callable, ttl: Optional[int] = None) -> Any:
        value = await self.get(key)
        if value is not None:
            return value
        result = factory()
        if asyncio.iscoroutine(result):
            result = await result
        # 不缓存错误响应：避免瞬时异常被缓存后持续向客户端返回错误
        # 错误响应的判定：dict 且 code 字段非 200
        if isinstance(result, dict) and result.get("code") not in (None, 200):
            return result
        await self.set(key, result, ttl)
        return result

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def clear(self) -> int:
        async with self._lock:
            n = len(self._store)
            self._store.clear()
            return n

    async def stats(self) -> Dict[str, Any]:
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "default_ttl": self._default_ttl,
            }


dashboard_cache = AsyncTTLCache(
    max_size=settings.DASHBOARD_CACHE_MAX_SIZE,
    default_ttl=settings.DASHBOARD_CACHE_TTL,
)
data_cache = AsyncTTLCache(
    max_size=settings.CACHE_MAX_SIZE,
    default_ttl=settings.CACHE_TTL,
)
