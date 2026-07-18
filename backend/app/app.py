from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.db.health import check_db_connection
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_db_connection()
    yield
    await dispose_engine()


app = FastAPI(
    title="Open Rag system",
    description="Open Rag system with Pinecone and Supabase",
    version="1.0.0",
    lifespan=lifespan,
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
