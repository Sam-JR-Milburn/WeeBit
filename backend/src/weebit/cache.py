from typing import AsyncGenerator
from aiocache import BaseCache
from aiocache.backends.redis import RedisCache
from aiocache.serializers import JsonSerializer

from weebit.config import settings

class CustomRedisCache(RedisCache):
    """Expose TTL functionality for Redis"""
    async def ttl(self, key: str) -> int:
        """Returns remaining TTL in seconds (-1 if no expire, -2 if key doesn't exist)."""
        return await self.client.ttl(self.build_key(key))

# Redis
redis_instance = CustomRedisCache(
    endpoint=settings.CACHE_URL,
    port=settings.CACHE_PORT,
    password=settings.CACHE_PASSWORD,
    namespace="weebit",
    pool_max_size=20,
    serializer=JsonSerializer(),
)
async def get_cache() -> AsyncGenerator[BaseCache, None]:
    try:
        yield redis_instance
    finally:
        pass