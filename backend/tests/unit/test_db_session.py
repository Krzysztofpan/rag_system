from unittest.mock import MagicMock, patch

import app.db.session as session_mod
from app.config import Settings
from app.db.session import get_engine


def _reset_engine() -> None:
    session_mod._engine = None
    session_mod._session_factory = None


def test_engine_uses_configured_pool_limits():
    _reset_engine()
    engine = MagicMock()
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost:5432/postgres",
        db_pool_size=5,
        db_max_overflow=5,
        db_pool_timeout=30,
        db_pool_recycle=300,
        app_env="production",
    )

    try:
        with patch("app.db.session.create_async_engine", return_value=engine) as create:
            result = get_engine(settings)

        assert result is engine
        create.assert_called_once()
        kwargs = create.call_args.kwargs
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 5
        assert kwargs["pool_timeout"] == 30
        assert kwargs["pool_recycle"] == 300
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["echo"] is False
    finally:
        _reset_engine()
