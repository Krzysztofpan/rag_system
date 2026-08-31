import pytest

from app.config import Settings
from app.lib.redis import (
    RedisConfigurationError,
    check_redis_connection,
    verify_redis_configuration,
)


def test_redis_url_is_built_from_host_and_port():
    settings = Settings(redis_host="localhost", redis_port=6380, redis_url=None)
    assert settings.redis_url == "redis://localhost:6380"


def test_redis_url_uses_default_port():
    settings = Settings(redis_host="redis", redis_url=None)
    assert settings.redis_url == "redis://redis:6379"


def test_explicit_redis_url_wins_over_host_and_port():
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_url="redis://redis:6379",
    )
    assert settings.redis_url == "redis://redis:6379"


def test_redis_url_is_missing_without_host_or_url():
    assert Settings(redis_host=None, redis_url=None).redis_url is None


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_missing_redis_url_is_rejected(monkeypatch, app_env):
    settings = Settings(app_env=app_env, redis_host=None, redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    with pytest.raises(RedisConfigurationError, match="REDIS_URL"):
        verify_redis_configuration()


@pytest.mark.parametrize("app_env", ["development", "production"])
async def test_ready_check_fails_without_redis(monkeypatch, app_env):
    settings = Settings(app_env=app_env, redis_host=None, redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    assert await check_redis_connection() == (False, "REDIS_URL is not configured")
