from typing import AsyncGenerator
from aiocache import Cache, BaseCache
from weebit.config import settings

# Redis
redis_instance = Cache(
    Cache.REDIS,
    endpoint=settings.REDIS_URL,
    port=settings.REDIS_PORT,
    namespace="weebit",
    pool_max_size=20
)
async def get_redis() -> AsyncGenerator[BaseCache, None]:
    try:
        yield redis_instance
    finally:
        pass