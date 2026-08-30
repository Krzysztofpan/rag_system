import pytest

from app.config import Settings
from app.lib.redis import (
    RedisConfigurationError,
    check_redis_connection,
    verify_redis_configuration,
)


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_missing_redis_url_is_rejected(monkeypatch, app_env):
    settings = Settings(app_env=app_env, redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    with pytest.raises(RedisConfigurationError, match="REDIS_URL"):
        verify_redis_configuration()


@pytest.mark.parametrize("app_env", ["development", "production"])
async def test_ready_check_fails_without_redis(monkeypatch, app_env):
    settings = Settings(app_env=app_env, redis_url=None)
    monkeypatch.setattr("app.lib.redis.get_settings", lambda: settings)
    assert await check_redis_connection() == (False, "REDIS_URL is not configured")
