from contextlib import asynccontextmanager
from typing import Literal

from app.services.document_indexing_service import DocumentIndexingService
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.services.parser_service import ParseQualityError, ParserFactory


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
    parser = ParserFactory(file).create_parser()
    indexing_service = DocumentIndexingService(parser)
    try:
        result = await indexing_service.ingest(file)
    except ParseQualityError as exc:
        return JSONResponse(
            status_code=422,
            content={"status": "rejected", "detail": str(exc), "report": exc.report},
        )

    if format == "markdown":
        filename = result.filename or "parsed.md"
        stem = filename.rsplit(".", 1)[0]
        return PlainTextResponse(
            content=result.markdown,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{stem}_parsed.md"',
                "X-Parse-Ok": "true" if result.ok else "false",
            },
        )

    # JSON keeps real newlines inside the string; clients must JSON-parse,
    # not copy the raw response body, or \\n will stay escaped.
    return {
        "status": "ok",
        "filename": result.filename,
        "content_type": result.content_type,
        "markdown": result.markdown,
        "report": result.report,
    }


@app.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "error", "detail": message},
    )
