from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.auth.jwt import verify_auth_configuration
from app.config import Settings, get_settings
from app.container import get_conversation_event_broker, get_run_registry
from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.lib.rate_limit import configure_rate_limiting
from app.routes.chat_stream_routes import chat_stream_router
from app.routes.conversation_routes import conversation_router
from app.routes.health_routes import health_router
from app.services.usage_limits import LimitExceededError


@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_auth_configuration()
    await check_db_connection()
    yield
    await get_run_registry().close()
    await get_conversation_event_broker().close()
    await dispose_engine()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    docs_enabled = not settings.is_production

    app = FastAPI(
        title="Open Rag system",
        description="Open Rag system with Pinecone and Supabase",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # Auth rides in the Authorization header, so cookies stay out of CORS.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    configure_rate_limiting(app)

    @app.exception_handler(LimitExceededError)
    async def limit_exceeded_handler(
        _request: Request,
        exc: LimitExceededError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.as_detail()},
        )

    app.include_router(health_router)
    app.include_router(conversation_router)
    app.include_router(chat_stream_router)
    return app


app = create_app()
