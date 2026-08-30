from __future__ import annotations

import logging

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


class RedisConfigurationError(RuntimeError):
    """REDIS_URL is required in production; checked while the app boots."""


def verify_redis_configuration() -> None:
    settings = get_settings()
    if settings.is_production and not settings.redis_url:
        raise RedisConfigurationError(
            "REDIS_URL is required when APP_ENV=production"
        )


def get_redis() -> Redis:
    global _redis
    settings = get_settings()
    if not settings.redis_url:
        raise RedisConfigurationError("REDIS_URL is not configured")
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_redis_connection() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.redis_url:
        if settings.is_production:
            message = "REDIS_URL is not configured"
            logger.warning("Redis connection check failed: %s", message)
            return False, message
        return True, "disabled"

    try:
        if await get_redis().ping():
            return True, "ok"
        message = "Unexpected Redis response"
        logger.warning("Redis connection check failed: %s", message)
        return False, message
    except Exception as exc:
        message = str(exc)
        logger.warning("Redis connection check failed: %s", message)
        return False, message


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
