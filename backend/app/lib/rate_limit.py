from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from limits.storage import storage_from_string
from limits.strategies import STRATEGIES
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.services.usage_limits import LimitCode


def get_rate_limit_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


def ingest_limit_value() -> str:
    return f"{get_settings().max_ingests_per_day}/day"


def ingest_error_message() -> str:
    limit = get_settings().max_ingests_per_day
    return f"Daily ingest limit reached ({limit})."


def message_limit_value() -> str:
    return f"{get_settings().max_messages_per_day}/day"


def message_error_message() -> str:
    limit = get_settings().max_messages_per_day
    return f"Daily message limit reached ({limit})."


# Import stays on memory:// so collecting tests does not need Redis.
# configure_rate_limiting rebinds to redis_url so uvicorn workers share counters.
limiter = Limiter(
    key_func=get_rate_limit_key,
    headers_enabled=True,
    storage_uri="memory://",
    strategy=get_settings().rate_limit_strategy,
    retry_after="delta-seconds",
    key_prefix="rag",
    key_style="endpoint",
)


def bind_limiter_storage(
    storage_uri: str,
    strategy: str | None = None,
) -> None:
    strategy = strategy or get_settings().rate_limit_strategy
    if (
        getattr(limiter, "_storage_uri", None) == storage_uri
        and getattr(limiter, "_strategy", None) == strategy
    ):
        return
    limiter._storage_uri = storage_uri
    limiter._strategy = strategy
    limiter._storage = storage_from_string(storage_uri)
    limiter._limiter = STRATEGIES[strategy](limiter._storage)


def configure_rate_limiting(
    app: FastAPI,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    bind_limiter_storage(
        settings.resolved_rate_limit_storage_uri,
        settings.rate_limit_strategy,
    )
    limiter.enabled = settings.limits_enabled
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    settings = get_settings()
    path = request.url.path
    if "/sources/" in path:
        code = LimitCode.max_ingests_per_day
        limit = settings.max_ingests_per_day
    elif path.rstrip("/").endswith("commands"):
        code = LimitCode.max_messages_per_day
        limit = settings.max_messages_per_day
    else:
        code = None
        limit = 0

    response = JSONResponse(
        status_code=429,
        content={
            "detail": {
                "code": code.value if code is not None else "rate_limit_exceeded",
                "message": exc.detail,
                "limit": limit,
                "current": limit,
            }
        },
    )
    view_limit = getattr(request.state, "view_rate_limit", None)
    app_limiter = getattr(request.app.state, "limiter", None)
    if app_limiter is not None and view_limit is not None:
        return app_limiter._inject_headers(response, view_limit)
    return response
