from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    global _engine

    settings = settings or get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=not settings.is_production,
            pool_pre_ping=True,
        )

    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
