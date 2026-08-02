from contextlib import asynccontextmanager
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.health import check_db_connection
from app.db.session import dispose_engine, get_session
from app.dependencies import DocumentIndexingServiceDep
from app.schemas.upload import (
    UploadResourceResponse,
    build_upload_quality,
    quality_from_rejected_report,
)
from app.services.conversation_store import ConversationStore
from app.services.parser import ParseQualityError

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateConversationRequest(BaseModel):
    user_id: UUID


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/conversations")
async def create_conversation(
    body: CreateConversationRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a conversation for a Supabase Auth user (MVP: pass user_id explicitly)."""
    store = ConversationStore(session)
    try:
        conversation = await store.create_conversation(user_id=body.user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "conversation_id": str(conversation.id),
        "user_id": str(conversation.user_id),
    }

@app.get("/conversations/{conversation_id}/resources")
async def get_resources(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    conversation_store = ConversationStore(session)

    conversation_resources = await conversation_store.get_conversation_resources(conversation_id)
    resources_count = len(conversation_resources)
    
    return {
        "count": resources_count,
        "conversation_resources": conversation_resources
    }

@app.post("/upload", response_model=UploadResourceResponse)
async def upload(
    indexing_service: DocumentIndexingServiceDep,
    file: UploadFile = File(...),
    conversation_id: UUID = Query(
        ..., description="conversations.id for this chat"
    ),
    session: AsyncSession = Depends(get_session),
) -> UploadResourceResponse:
    """Business outcomes always return HTTP 200 with status ready|rejected."""
    conversation_store = ConversationStore(session)
    try:
        await conversation_store.get_conversation(conversation_id)
    except ValueError as exc:
        return UploadResourceResponse(
            status="rejected",
            error=str(exc),
        )

    try:
        result = await indexing_service.ingest(
            file,
            conversation_id=conversation_id,
        )
    except ParseQualityError as exc:
        return UploadResourceResponse(
            status="rejected",
            document_id=(
                str(exc.document_id) if exc.document_id is not None else None
            ),
            quality=quality_from_rejected_report(exc.report),
            error=str(exc),
        )

    return UploadResourceResponse(
        status="ready",
        document_id=str(result.document_id),
        parsed_content=result.parsed_content,
        quality=build_upload_quality(
            parse_report=result.parse_report,
            chunk_quality=result.chunk_quality,
        ),
        error=None,
    )


@app.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "error", "detail": message},
    )
