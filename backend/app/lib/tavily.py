from tavily import AsyncTavilyClient

from functools import lru_cache

@lru_cache(maxsize=1)
def get_tavily_client() -> AsyncTavilyClient:
    return AsyncTavilyClient()