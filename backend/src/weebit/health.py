import time
import asyncio
from typing import Optional, Literal, Dict
from uuid import uuid4
import logging

from redis import RedisError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from weebit.database import get_db
from weebit.cache import TTLCache, get_strict_cache

health_router = APIRouter(tags=["Health Check Endpoints"])

class BasicHealthResponse(BaseModel):
    status: Literal["ok", "bad"]

class DatabaseHealthResponse(BaseModel):
    status: Literal["ok", "bad"]
    latency_ms: Optional[float] = None

class CacheHealthResponse(BaseModel):
    status: Literal["ok", "bad"]
    set_ms: Optional[float] = None
    get_ms: Optional[float] = None
    ttl_ms: Optional[float] = None
    reason: Optional[str] = None

@health_router.get(
    "/health",
    response_model=BasicHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health/liveness check",
)
async def health_check():
    """Simple liveness check for an elementary load balancer."""

    return BasicHealthResponse(status="ok")


@health_router.get(
    "/health/database",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "If the database can't be reached",
            "content": {
                "application/problem+json": {
                    "schema": DatabaseHealthResponse.model_json_schema(),
                    "example": {
                        "status": "bad"
                    }
                }
            }
        }
    },
    summary="Database connectivity check."
)
async def database_health_check(response: Response, db: AsyncSession = Depends(get_db)):
    """Checks if the database can be reached."""

    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return DatabaseHealthResponse(status="ok", latency_ms=elapsed_ms)
    except (SQLAlchemyError, OSError) as e:
        logger.exception(f"Database health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(status="bad")
    except Exception as e:
        logger.exception(f"Database health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(status="bad")


@health_router.get(
    "/health/cache",
    response_model=CacheHealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "If the cache can't be reached",
            "content": {
                "application/problem+json": {
                    "schema": CacheHealthResponse.model_json_schema(),
                    "example": {
                        "status": "bad",
                        "reason": "timeout",
                    }
                }
            }
        }
    },
    summary="Cache health check."
)
async def cache_health_check(cache: TTLCache = Depends(get_strict_cache)):
    """Checks if the cache can be reached and returns the timings for a set, get and ttl operation."""

    test_key = f"health_check:{uuid4().hex}"
    timings = {}

    async def run_checks() -> Dict[str, float]:

        # Test cache set
        start = time.perf_counter()
        result = await cache.set(test_key, "ok", ttl=10)
        timings['set_ms'] = round((time.perf_counter() - start) * 1000.0, 2)

        if not result:
            raise RuntimeError("Cache SET operation failed.")

        # Test cache get
        start = time.perf_counter()
        value = await cache.get(test_key)
        timings['get_ms'] = round((time.perf_counter() - start) * 1000.0, 2)
        if not value:
            raise RuntimeError("Cache GET operation failed: empty value returned.")

        # TTL
        start = time.perf_counter()
        try:
            ttl = await cache.get_ttl(test_key)
            print(f"DEBUG: raw ttl returned from cache.ttl(): {ttl}")
        except Exception as e:
            logger.exception(f"Cache TTL operation failed: {e}")
            print(f"{e.__class__.__name__}: {e}")
            raise
        timings["ttl_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )
        if ttl <= 0:
            raise RuntimeError("Cache TTL verification failed")

        return timings

    try:
        timing_results = await asyncio.wait_for(run_checks(), timeout=0.5)
        return CacheHealthResponse(status="ok", **timing_results)
    except asyncio.TimeoutError:
        logger.warning("Redis health check timed out (500ms+)")
        return CacheHealthResponse(status="bad", reason="timeout")
    except Exception as e:
        logger.exception(f"Redis health check failed: {e}")
        return CacheHealthResponse(status="bad", reason="generic")
    finally:
        try:
            await asyncio.wait_for(
                cache.delete(test_key),
                timeout=0.25,
            )
        except (RedisError, OSError, asyncio.TimeoutError) as e:
            logger.warning("Failed to cleanup cache health check key due to network/Redis error: %s", e)
        except asyncio.CancelledError:
            # Handle task cancellation cleanly if the request is aborted mid-flight
            raise