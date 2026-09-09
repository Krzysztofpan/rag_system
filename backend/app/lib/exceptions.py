from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.usage_limits import LimitExceededError


def register_limit_exceeded_handler(app: FastAPI) -> None:
    @app.exception_handler(LimitExceededError)
    async def limit_exceeded_handler(
        _request: Request,
        exc: LimitExceededError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.as_detail()},
        )
