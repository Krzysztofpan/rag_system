import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.health import check_db_connection
from app.lib.pinecone_health import check_pinecone_connection

health_router = APIRouter(tags=["health"])


def _status_response(ok: bool, content: dict) -> JSONResponse:
    return JSONResponse(
        status_code=200 if ok else 503,
        content=content,
    )


@health_router.get("/live")
async def live():
    return {"status": "ok"}


@health_router.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    return _status_response(
        ok,
        {"status": "ok" if ok else "error", "detail": message},
    )


@health_router.get("/ready")
async def ready():
    (db_ok, db_message), (pinecone_ok, pinecone_message) = await asyncio.gather(
        check_db_connection(),
        check_pinecone_connection(),
    )
    ok = db_ok and pinecone_ok
    return _status_response(
        ok,
        {
            "status": "ok" if ok else "error",
            "checks": {
                "database": db_message,
                "pinecone": pinecone_message,
            },
        },
    )
