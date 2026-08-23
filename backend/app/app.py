from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.auth.jwt import verify_auth_configuration
from app.config import get_settings
from app.container import get_run_registry
from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.routes.chat_stream_routes import chat_stream_router
from app.routes.conversation_routes import conversation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_auth_configuration()
    await check_db_connection()
    yield
    await get_run_registry().close()
    await dispose_engine()


app = FastAPI(
    title="Open Rag system",
    description="Open Rag system with Pinecone and Supabase",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    # Auth rides in the Authorization header, so cookies stay out of CORS.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "error", "detail": message},
    )

app.include_router(conversation_router)
app.include_router(chat_stream_router)
