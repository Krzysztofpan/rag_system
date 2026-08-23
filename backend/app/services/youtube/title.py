from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_OEMBED_URL = "https://www.youtube.com/oembed?url={url}&format=json"
_TIMEOUT_SECONDS = 10


def fetch_youtube_title(url: str) -> str | None:
    request = Request(
        _OEMBED_URL.format(url=quote(url, safe="")),
        headers={"User-Agent": "rag-system/1.0"},
    )
    try:
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    return title.strip()
