from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from pinecone import PineconeException

from app.lib.pinecone_health import check_pinecone_connection


def _settings(*, api_key: str | None = "pc-key", index: str = "rag-system"):
    return SimpleNamespace(pinecone_api_key=api_key, pinecone_index=index)


def _async_client(describe):
    pc = MagicMock()
    pc.describe_index = describe
    pc.__aenter__ = AsyncMock(return_value=pc)
    pc.__aexit__ = AsyncMock(return_value=False)
    return pc


async def test_check_pinecone_connection_requires_api_key():
    with patch(
        "app.lib.pinecone_health.get_settings",
        return_value=_settings(api_key=None),
    ):
        ok, message = await check_pinecone_connection()

    assert ok is False
    assert message == "PINECONE_API_KEY is not configured"


async def test_check_pinecone_connection_ok_when_index_ready():
    description = SimpleNamespace(status=SimpleNamespace(ready=True, state="Ready"))
    pc = _async_client(AsyncMock(return_value=description))

    with (
        patch(
            "app.lib.pinecone_health.get_settings",
            return_value=_settings(),
        ),
        patch("app.lib.pinecone_health.PineconeAsyncio", return_value=pc),
    ):
        ok, message = await check_pinecone_connection()

    assert ok is True
    assert message == "ok"
    pc.describe_index.assert_awaited_once_with(name="rag-system")


async def test_check_pinecone_connection_fails_when_index_not_ready():
    description = SimpleNamespace(
        status=SimpleNamespace(ready=False, state="Initializing")
    )
    pc = _async_client(AsyncMock(return_value=description))

    with (
        patch(
            "app.lib.pinecone_health.get_settings",
            return_value=_settings(),
        ),
        patch("app.lib.pinecone_health.PineconeAsyncio", return_value=pc),
    ):
        ok, message = await check_pinecone_connection()

    assert ok is False
    assert message == "Pinecone index 'rag-system' is not ready (state=Initializing)"


async def test_check_pinecone_connection_fails_on_sdk_error():
    pc = _async_client(AsyncMock(side_effect=PineconeException("index missing")))

    with (
        patch(
            "app.lib.pinecone_health.get_settings",
            return_value=_settings(),
        ),
        patch("app.lib.pinecone_health.PineconeAsyncio", return_value=pc),
    ):
        ok, message = await check_pinecone_connection()

    assert ok is False
    assert message == "index missing"
