import logging

from pinecone import PineconeAsyncio, PineconeException

from app.config import get_settings

logger = logging.getLogger(__name__)


def _index_ready_state(description: object) -> tuple[bool, str | None]:
    status = getattr(description, "status", None)
    if isinstance(status, dict):
        ready = status.get("ready")
        state = status.get("state")
    else:
        ready = getattr(status, "ready", None)
        state = getattr(status, "state", None)
    return bool(ready), str(state) if state is not None else None


async def check_pinecone_connection() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.pinecone_api_key:
        message = "PINECONE_API_KEY is not configured"
        logger.warning("Pinecone connection check failed: %s", message)
        return False, message

    try:
        async with PineconeAsyncio(api_key=settings.pinecone_api_key) as pc:
            description = await pc.describe_index(name=settings.pinecone_index)
    except PineconeException as exc:
        message = str(exc)
        logger.warning("Pinecone connection check failed: %s", message)
        return False, message
    except Exception as exc:
        message = str(exc) or type(exc).__name__
        logger.warning("Pinecone connection check failed: %s", message)
        return False, message

    ready, state = _index_ready_state(description)
    if not ready:
        message = f"Pinecone index '{settings.pinecone_index}' is not ready"
        if state:
            message = f"{message} (state={state})"
        logger.warning("Pinecone connection check failed: %s", message)
        return False, message

    logger.info("Pinecone connection verified")
    return True, "ok"
