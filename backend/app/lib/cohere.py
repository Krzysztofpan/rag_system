from functools import lru_cache

import cohere

from app.config import get_settings


@lru_cache
def get_cohere_client() -> cohere.AsyncClientV2:
    api_key = get_settings().cohere_api_key
    if not api_key:
        raise RuntimeError("COHERE_API_KEY is not configured")
    return cohere.AsyncClientV2(api_key=api_key)
