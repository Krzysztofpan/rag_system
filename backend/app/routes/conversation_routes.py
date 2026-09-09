import json
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError

from app.auth.deps import get_current_user
from app.dependencies import (
    ConversationEventBrokerDep,
    ConversationServiceDep,
    CurrentUserDep,
    DocumentServiceDep,
    MessageServiceDep,
    UsageLimitServiceDep,
)
from app.services.conversation.documents_catalog import refresh_and_publish_documents_summary
from app.services.conversation.conversation_events import HEARTBEAT
from app.schemas.chunk import ChunkResponse
from app.schemas.conversation import (
    ConversationResponse,
    CreateConversationResponse,
    DeleteConversationResponse,
    GetConversationsResponse,
    conversation_from_model,
)
from app.schemas.message import GetConversationMessagesResponse
from app.schemas.source import (
    DeleteSourceResponse,
    GetSourcesResponse,
    SourceReportResponse,
    report_from_document_report,
    source_from_document,
)

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@conversation_router.post("/", response_model=CreateConversationResponse)
async def create_conversation(
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    usage_limits: UsageLimitServiceDep,
) -> CreateConversationResponse:
    """Create a conversation for the authenticated Supabase Auth user."""
    await usage_limits.enforce_create_conversation(current_user.user_id)
    try:
        conversation = await conversation_service.create_conversation(user_id=current_user.user_id)
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Unknown user") from exc
    return CreateConversationResponse(
        conversation_id=str(conversation.id),
        user_id=str(conversation.user_id),
    )

@conversation_router.get("/", response_model=GetConversationsResponse)
async def get_conversations(
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> GetConversationsResponse:
    conversations = await conversation_service.get_conversations(user_id=current_user.user_id)

    return GetConversationsResponse(
        conversations=[conversation_from_model(c) for c in conversations],
    )


@conversation_router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> ConversationResponse:
    try:
        conversation = await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return conversation_from_model(conversation)


@conversation_router.get("/{conversation_id}/events")
async def conversation_events(
    conversation_id: UUID,
    request: Request,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    broker: ConversationEventBrokerDep,
) -> StreamingResponse:
    try:
        await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def generate():
        subscription = await broker.subscribe(conversation_id)
        async for item in subscription.events():
            if await request.is_disconnected():
                break
            if item is HEARTBEAT:
                yield ": heartbeat\n\n"
            else:
                yield (
                    f"data: {json.dumps(item, separators=(',', ':'))}\n\n"
                )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@conversation_router.delete('/{conversation_id}', response_model=DeleteConversationResponse)
async def delete_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> DeleteConversationResponse:
    try:
        deleted_conversation = await conversation_service.delete_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DeleteConversationResponse(
        deleted_conversation=conversation_from_model(deleted_conversation),
    )

@conversation_router.patch('/{conversation_id}/title')
async def change_conversation_title(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    message_service: MessageServiceDep,
    title: str = Body(...),
):
    try:
        updated_title = await conversation_service.change_conversation_title(
            conversation_id,
            user_id=current_user.user_id,
            title=title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return updated_title


@conversation_router.get(
    "/{conversation_id}/messages",
    response_model=GetConversationMessagesResponse,
)
async def get_conversation_messages(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    message_service: MessageServiceDep,
    limit: Annotated[int, Query(ge=1)] = 20,
    before_id: UUID | None = None,
):
    await conversation_service.get_conversation(conversation_id, user_id=current_user.user_id)
    message_page = await message_service.get_messages(conversation_id, user_id=current_user.user_id, limit=limit, before_id=before_id)
    
    return GetConversationMessagesResponse(
        messages=message_page.messages,
        has_more=message_page.has_more,
    )


@conversation_router.get(
    "/{conversation_id}/chunks/{chunk_id}",
    response_model=ChunkResponse,
)
async def get_chunk(
    conversation_id: UUID,
    chunk_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> ChunkResponse:
    try:
        chunk, document = await document_service.get_chunk(
            conversation_id,
            chunk_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ChunkResponse(
        id=chunk.id,
        document_id=document.id,
        filename=document.filename,
        content=chunk.content,
        pages=chunk.pages,
        chunk_index=chunk.chunk_index,
    )


@conversation_router.get(
    "/{conversation_id}/sources",
    response_model=GetSourcesResponse,
)
async def get_sources(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> GetSourcesResponse:
    try:
        documents = await document_service.get_conversation_documents(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    sources = [source_from_document(document) for document in documents]

    return GetSourcesResponse(
        count=len(sources),
        conversation_sources=sources,
    )


@conversation_router.delete("/{conversation_id}/sources/{document_id}")
async def delete_source(
    conversation_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
    background_tasks: BackgroundTasks,
):
    try:
        deleted_document = await document_service.delete_document(
            conversation_id,
            document_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background_tasks.add_task(
        refresh_and_publish_documents_summary,
        conversation_id,
        current_user.user_id,
    )
    return DeleteSourceResponse(deleted_document=deleted_document)


@conversation_router.patch("/{conversation_id}/sources/{document_id}")
async def change_source_name(
    conversation_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
    name: str = Body(...),
):
    try:
        updated_name = await document_service.change_document_name(
            conversation_id,
            document_id,
            name,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return updated_name


@conversation_router.get(
    "/{conversation_id}/sources/{document_id}/report",
    response_model=SourceReportResponse,
)
async def get_source_report(
    conversation_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> SourceReportResponse:
    try:
        report = await document_service.get_report(
            conversation_id,
            document_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return report_from_document_report(report)
