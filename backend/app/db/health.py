import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)


async def check_db_connection() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.database_url:
        message = "DATABASE_URL is not configured"
        logger.warning("Database connection check failed: %s", message)
        return False, message

    try:
        session_factory = get_session_factory(settings)
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar_one() != 1:
                message = "Unexpected database response"
                logger.warning("Database connection check failed: %s", message)
                return False, message
    except RuntimeError as exc:
        message = str(exc)
        logger.warning("Database connection check failed: %s", message)
        return False, message
    except SQLAlchemyError as exc:
        message = str(exc.__cause__ or exc)
        logger.warning("Database connection check failed: %s", message)
        return False, message

    logger.info("Database connection verified")
    return True, "ok"
