from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from fastapi import Depends, FastAPI, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.health import check_db_connection
from app.db.session import dispose_engine, get_session
from app.services.chunker import ChunkerFactory
from app.services.doc_store import DocumentStore
from app.services.document_indexing_service import DocumentIndexingService
from app.services.parser import ParseQualityError, ParserFactory


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
    session: AsyncSession = Depends(get_session),
):
    parser = ParserFactory.create_parser(file)
    chunker = ChunkerFactory.create_chunker(file.content_type)
    doc_store = DocumentStore(session)
    indexing_service = DocumentIndexingService(parser, chunker, doc_store=doc_store)
    try:
        result = await indexing_service.ingest(file)
    except ParseQualityError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": "rejected",
                "document_id": (
                    str(exc.document_id) if exc.document_id is not None else None
                ),
                "detail": str(exc),
                "report": exc.report,
            },
        )

    return {
        "status": "ok",
        "document_id": str(result.document_id),
        "result": [asdict(chunk) for chunk in result.chunks],
        "quality": {
            "parse_report": result.parse_report,
            "chunk_quality": {
                key: value
                for key, value in result.chunk_quality.items()
                if key != "kept_indexes"
            },
        },
    }


@app.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "error", "detail": message},
    )
