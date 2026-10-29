"""Cache service supporting Redis with graceful in-memory fallback."""

import logging
import time
from typing import Optional, Any, Dict, Tuple
import redis.asyncio as aioredis
from memetek.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async cache provider with Redis and In-Memory fallback."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._in_memory: Dict[str, Tuple[Any, float]] = {}
        self._redis_available: bool = False

    async def connect(self) -> None:
        """Attempt to connect to Redis, fallback to in-memory if unavailable."""
        try:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            await self._redis.ping()
            self._redis_available = True
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            self._redis_available = False
            logger.warning("Redis unavailable (%s). Falling back to in-memory cache.", e)

    async def close(self) -> None:
        """Close cache connections."""
        if self._redis and self._redis_available:
            try:
                await self._redis.close()
            except Exception:
                pass

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value by key."""
        if self._redis_available and self._redis:
            try:
                return await self._redis.get(key)
            except Exception as e:
                logger.warning("Redis GET failed for key %s (%s). Using in-memory.", key, e)

        # Fallback to in-memory
        if key in self._in_memory:
            value, expires_at = self._in_memory[key]
            if time.time() < expires_at:
                return value
            else:
                del self._in_memory[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set cached value with time-to-live in seconds."""
        if self._redis_available and self._redis:
            try:
                await self._redis.set(key, value, ex=ttl)
                return
            except Exception as e:
                logger.warning("Redis SET failed for key %s (%s). Using in-memory.", key, e)

        # Fallback to in-memory
        self._in_memory[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        """Remove key from cache."""
        if self._redis_available and self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        self._in_memory.pop(key, None)

    async def increment(self, key: str, ttl: int = 60) -> int:
        """Increment integer key for rate-limiting with expiration."""
        if self._redis_available and self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                res = await pipe.execute()
                return int(res[0])
            except Exception as e:
                logger.warning("Redis INCR failed for key %s (%s). Using in-memory.", key, e)

        # Fallback to in-memory
        now = time.time()
        if key in self._in_memory:
            curr_val, exp = self._in_memory[key]
            if now < exp:
                new_val = int(curr_val) + 1
                self._in_memory[key] = (new_val, exp)
                return new_val
        self._in_memory[key] = (1, now + ttl)
        return 1

    @property
    def is_redis(self) -> bool:
        """Check if Redis backend is active."""
        return self._redis_available


cache = CacheService(settings.REDIS_URL)
