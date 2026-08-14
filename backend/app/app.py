from contextlib import asynccontextmanager
from uuid import UUID
from langchain_core.messages import HumanMessage
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.auth.jwt import verify_auth_configuration
from app.config import get_settings
from app.routes.conversation_routes import conversation_router
from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.dependencies import ConversationServiceDep, CurrentUserDep, DocumentIndexingServiceDep
from app.schemas.source import (
    SourceReportResponse,
    SourceResponse,
    UploadSourceResponse,
)
from app.schemas.upload import (
    build_upload_quality,
    quality_from_rejected_report,
)
from app.services.parser import ParseQualityError
from app.schemas.chat import ChatRequestBody
from app.agent.agent_orchestrator import get_agent_orchestrator

@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_auth_configuration()
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
    allow_origins=get_settings().cors_origins,
    # Auth rides in the Authorization header, so cookies stay out of CORS.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/upload", response_model=UploadSourceResponse)
async def upload(
    indexing_service: DocumentIndexingServiceDep,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    file: UploadFile = File(...),
    conversation_id: UUID = Query(
        ..., description="conversations.id for this chat"
    ),
) -> UploadSourceResponse:
    """Business outcomes always return HTTP 200; failures use source.status=failed or source=null."""
    try:
        await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        # Authorization failure, not a business outcome: same 404 as elsewhere.
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filename = file.filename or "unknown"
    content_type = file.content_type

    try:
        result = await indexing_service.ingest(
            file,
            conversation_id=conversation_id,
        )
    except ParseQualityError as exc:
        source = None
        report = None
        if exc.document_id is not None:
            source = SourceResponse(
                id=str(exc.document_id),
                filename=filename,
                content_type=content_type,
                status="failed",
                error=str(exc),
                chunk_count=0,
            )
            report = SourceReportResponse(
                document_id=str(exc.document_id),
                parsed_content=exc.parsed_content,
                quality=quality_from_rejected_report(exc.report),
            )
        return UploadSourceResponse(
            source=source,
            report=report,
            error=str(exc),
        )

    quality = build_upload_quality(
        parse_report=result.parse_report,
        chunk_quality=result.chunk_quality,
    )
    return UploadSourceResponse(
        source=SourceResponse(
            id=str(result.document_id),
            filename=filename,
            content_type=content_type,
            status="ready",
            error=None,
            chunk_count=len(result.chunk_ids),
        ),
        report=SourceReportResponse(
            document_id=str(result.document_id),
            parsed_content=result.parsed_content,
            quality=quality,
        ),
        error=None,
    )



@app.post("/chat")
async def chat(
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    body: ChatRequestBody,
):
    await conversation_service.get_conversation(body.conversation_id, user_id=current_user.user_id)
    agent = get_agent_orchestrator()
    agent_response = agent.invoke(
        {"messages": [HumanMessage(body.message)]},
        context={"conversation_id": body.conversation_id, "user_id": current_user.user_id, "document_ids": body.document_ids},
    )

    return {
        "response": agent_response
    }


@app.get("/health/db")
async def health_db():
    ok, message = await check_db_connection()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "error", "detail": message},
    )

app.include_router(conversation_router)