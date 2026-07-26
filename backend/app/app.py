from contextlib import asynccontextmanager
from typing import Literal

from app.services.document_indexing_service import DocumentIndexingService
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.services.parser import ParseQualityError, ParserFactory
from app.services.chunker import ChunkerFactory

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


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    format: Literal["json", "markdown"] = Query(
        "json",
        description=(
            "json: markdown + quality report for UI preview. "
            "markdown: raw text/markdown (easy to save/open in a viewer)."
        ),
    ),
):
    parser = ParserFactory.create_parser(file)
    chunker = ChunkerFactory.create_chunker(file.content_type)
    indexing_service = DocumentIndexingService(parser, chunker)
    try:
        result = await indexing_service.ingest(file)
        """ print(result, len(result)) """
    except ParseQualityError as exc:
        return JSONResponse(
            status_code=422,
            content={"status": "rejected", "detail": str(exc), "report": exc.report},
        )

    return {
        "status": "ok",
        "result": result
    }

@app.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "error", "detail": message},
    )
