import logging
logger = logging.getLogger(__name__)

from typing import AsyncGenerator, Any

import asyncio
from aiocache import BaseCache, RedisCache
from abc import ABC, abstractmethod

import redis.asyncio as aioredis

from aiocache.serializers import JsonSerializer

from weebit.config import settings

import time

# For the fail-open cache.
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_after: float = 15.0):
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None and (
            time.monotonic() - self._opened_at < self.reset_after
        )

    def success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()  # (re)open; after reset_after, a probe is allowed


class TTLCache(BaseCache, ABC):
    """Abstract Class combining BaseCache + TTL queries."""

    MAX_BACKGROUND_TASKS = 100
    def __init__(self, *args, breaker_threshold: int = 3, breaker_reset: float = 15.0, **kwargs):
        super().__init__(*args, **kwargs)
        self._breaker = CircuitBreaker(breaker_threshold, breaker_reset)
        self._bg_tasks: set[asyncio.Task] = set()

    # TTL Methods
    async def get_ttl(self, key, namespace=None):
        """Remaining TTL in seconds, or None if the key is missing or has no expiry."""
        ns_key = self.build_key(key, namespace)
        return await asyncio.wait_for(self._ttl(ns_key), self.timeout)

    @abstractmethod
    async def _ttl(self, key):
        """Backend primitive; receives the already-namespaced key."""


class RedisTTLCache(TTLCache, RedisCache):
    """Concrete, strict, TTL-supported implementation of the RedisCache"""

    def __init__(self, *, redis_url: str, timeout: float = 0.25, max_connections: int = 20,
                 ssl_cert_reqs: str | None = None, **kwargs):
        super().__init__(**kwargs)  # builds the default client; no connection is made yet
        extra = {"ssl_cert_reqs": ssl_cert_reqs} if ssl_cert_reqs else {}
        self.client = aioredis.from_url(redis_url, max_connections=max_connections, socket_connect_timeout=timeout, socket_timeout=timeout, **extra)

    async def _ttl(self, key):
        remaining = await self.raw("ttl", key)
        return remaining if remaining >= 0 else None


_strict_redis_instance: TTLCache = RedisTTLCache(
    namespace="weebit",
    serializer=JsonSerializer(),
    timeout=0.25,
    redis_url=settings.redis_url,
    ssl_cert_reqs=settings.CACHE_SSL_CERT_REQS if settings.CACHE_SSL else None,
)
async def get_strict_cache() -> AsyncGenerator[TTLCache, None]:
    try:
        yield _strict_redis_instance
    finally:
        pass

FAIL_OPEN_ERRORS = (aioredis.RedisError, OSError, asyncio.TimeoutError)

class FailOpenTTLCache(TTLCache, ABC):
    """Abstract Class adding fail-open behavior and circuit-breaking to TTL caches."""

    async def _safe_op(self, op_name: str, default: Any, coro: Any) -> Any:
        if self._breaker.is_open:
            logger.warning("Cache circuit breaker is OPEN. Failing open for operation: %s", op_name)
            return default

        try:
            result = await coro
            self._breaker.success()
            return result
        except FAIL_OPEN_ERRORS as e:
            self._breaker.failure()
            logger.warning("Cache operation '%s' failed (failing open): %s", op_name, e)
            return default

    # Overridden Fail-Open Core Methods
    async def get(self, key: str, default: Any = None, loads_fn: Any = None, namespace: str | None = None, _conn: Any = None, **kwargs: Any) -> Any:
        return await self._safe_op("get", default, super().get(key, default=default, loads_fn=loads_fn, namespace=namespace, _conn=_conn, **kwargs))

    async def set(self, key: str, value: Any, ttl: int | float | None = None, dumps_fn: Any = None, namespace: str | None = None, _cas_token: Any = None, _conn: Any = None) -> bool:
        return await self._safe_op("set", False, super().set(key, value, ttl=ttl, dumps_fn=dumps_fn, namespace=namespace, _cas_token=_cas_token, _conn=_conn))

    async def add(self, key: str, value: Any, ttl: int | float | None = None, dumps_fn: Any = None, namespace: str | None = None, _conn: Any = None) -> bool:
        return await self._safe_op("add", False, super().add(key, value, ttl=ttl, dumps_fn=dumps_fn, namespace=namespace, _conn=_conn))

    async def delete(self, key: str, namespace: str | None = None, _conn: Any = None) -> int:
        return await self._safe_op("delete", 0, super().delete(key, namespace=namespace, _conn=_conn))

    async def exists(self, key: str, namespace: str | None = None, _conn: Any = None) -> bool:
        return await self._safe_op("exists", False, super().exists(key, namespace=namespace, _conn=_conn))

    async def expire(self, key: str, ttl: int | float, namespace: str | None = None, _conn: Any = None) -> bool:
        return await self._safe_op("expire", False, super().expire(key, ttl=ttl, namespace=namespace, _conn=_conn))

    async def clear(self, namespace: str | None = None, _conn: Any = None) -> bool:
        return await self._safe_op("clear", False, super().clear(namespace=namespace, _conn=_conn))

    async def get_ttl(self, key, namespace=None):
        async def _fetch():
            return await super().get_ttl(key, namespace=namespace)
        # Returns -2 as a safe default indicating missing/unavailable TTL state
        return await self._safe_op("get_ttl", -2, _fetch())


class FailOpenRedisTTLCache(FailOpenTTLCache, RedisTTLCache):
    """Fail-open TTL-supported implementation of the RedisCache"""
    pass

_failopen_redis_instance: FailOpenTTLCache = FailOpenRedisTTLCache(
    namespace="weebit",
    serializer=JsonSerializer(),
    timeout=0.25,
    redis_url=settings.redis_url,
    ssl_cert_reqs=settings.CACHE_SSL_CERT_REQS if settings.CACHE_SSL else None,
)

async def get_failopen_cache() -> AsyncGenerator[FailOpenTTLCache, None]:
    try:
        yield _failopen_redis_instance
    finally:
        pass