from functools import lru_cache

from groq import AsyncGroq

from app.config import get_settings


@lru_cache
def get_groq_client() -> AsyncGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return AsyncGroq(
        api_key=settings.groq_api_key,
        base_url=settings.prompt_guard_url,
        timeout=settings.prompt_guard_timeout_sec,
    )
