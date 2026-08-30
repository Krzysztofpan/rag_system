import pytest

from app.config import Settings
from app.lib.redis import (
    RedisConfigurationError,
    check_redis_connection,
    verify_redis_configuration,
)


def test_production_requires_redis_url(monkeypatch):
    settings = Settings(app_env="production", redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    with pytest.raises(RedisConfigurationError, match="REDIS_URL"):
        verify_redis_configuration()


def test_development_allows_missing_redis_url(monkeypatch):
    settings = Settings(app_env="development", redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    verify_redis_configuration()


async def test_ready_check_is_disabled_without_redis_in_development(monkeypatch):
    settings = Settings(app_env="development", redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    assert await check_redis_connection() == (True, "disabled")


async def test_ready_check_fails_without_redis_in_production(monkeypatch):
    settings = Settings(app_env="production", redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    assert await check_redis_connection() == (False, "REDIS_URL is not configured")
