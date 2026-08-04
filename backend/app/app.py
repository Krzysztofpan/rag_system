from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.health import check_db_connection
from app.db.session import dispose_engine, get_session
from app.dependencies import DocumentIndexingServiceDep
from app.schemas.conversation import (
    CreateConversationRequest,
    CreateConversationResponse,
)
from app.schemas.resource import (
    GetResourcesResponse,
    ResourceReportResponse,
    ResourceResponse,
    UploadResourceResponse,
    report_from_document_report,
    resource_from_document,
)
from app.schemas.upload import (
    build_upload_quality,
    quality_from_rejected_report,
)
from app.services.conversation_store import ConversationStore
from app.services.doc_store import DocumentStore
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


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    body: CreateConversationRequest,
    session: AsyncSession = Depends(get_session),
) -> CreateConversationResponse:
    """Create a conversation for a Supabase Auth user (MVP: pass user_id explicitly)."""
    store = ConversationStore(session)
    try:
        conversation = await store.create_conversation(user_id=body.user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateConversationResponse(
        conversation_id=str(conversation.id),
        user_id=str(conversation.user_id),
    )


@app.get(
    "/conversations/{conversation_id}/resources",
    response_model=GetResourcesResponse,
)
async def get_resources(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> GetResourcesResponse:
    conversation_store = ConversationStore(session)

    conversation_resources = await conversation_store.get_conversation_resources(
        conversation_id
    )
    resources = [resource_from_document(document) for document in conversation_resources]

    return GetResourcesResponse(
        count=len(resources),
        conversation_resources=resources,
    )


@app.get(
    "/conversations/{conversation_id}/resources/{document_id}/report",
    response_model=ResourceReportResponse,
)
async def get_resource_report(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ResourceReportResponse:
    document_store = DocumentStore(session)
    try:
        document = await document_store.get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if document.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Document not found in conversation")

    report = await document_store.get_report(document_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return report_from_document_report(report)


@app.post("/upload", response_model=UploadResourceResponse)
async def upload(
    indexing_service: DocumentIndexingServiceDep,
    file: UploadFile = File(...),
    conversation_id: UUID = Query(
        ..., description="conversations.id for this chat"
    ),
    session: AsyncSession = Depends(get_session),
) -> UploadResourceResponse:
    """Business outcomes always return HTTP 200; failures use resource.status=failed or resource=null."""
    conversation_store = ConversationStore(session)
    try:
        await conversation_store.get_conversation(conversation_id)
    except ValueError as exc:
        return UploadResourceResponse(error=str(exc))

    filename = file.filename or "unknown"
    content_type = file.content_type

    try:
        result = await indexing_service.ingest(
            file,
            conversation_id=conversation_id,
        )
    except ParseQualityError as exc:
        resource = None
        report = None
        if exc.document_id is not None:
            resource = ResourceResponse(
                id=str(exc.document_id),
                filename=filename,
                content_type=content_type,
                status="failed",
                error=str(exc),
                chunk_count=0,
            )
            report = ResourceReportResponse(
                document_id=str(exc.document_id),
                parsed_content=exc.parsed_content,
                quality=quality_from_rejected_report(exc.report),
            )
        return UploadResourceResponse(
            resource=resource,
            report=report,
            error=str(exc),
        )

    quality = build_upload_quality(
        parse_report=result.parse_report,
        chunk_quality=result.chunk_quality,
    )
    return UploadResourceResponse(
        resource=ResourceResponse(
            id=str(result.document_id),
            filename=filename,
            content_type=content_type,
            status="ready",
            error=None,
            chunk_count=len(result.chunk_ids),
        ),
        report=ResourceReportResponse(
            document_id=str(result.document_id),
            parsed_content=result.parsed_content,
            quality=quality,
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
