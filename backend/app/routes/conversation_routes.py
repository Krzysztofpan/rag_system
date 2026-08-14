from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.session import get_session
from app.dependencies import (
    ConversationServiceDep,
    CurrentUserDep,
)
from app.schemas.conversation import (
    CreateConversationResponse,
    GetConversationsResponse,
    conversation_from_model,
    DeleteConversationResponse
)
from app.schemas.source import (
    DeleteSourceResponse,
    GetSourcesResponse,
    SourceReportResponse,
    report_from_document_report,
    source_from_document,
)
from app.services.doc_store import DocumentStore

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@conversation_router.post("/", response_model=CreateConversationResponse)
async def create_conversation(
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> CreateConversationResponse:
    """Create a conversation for the authenticated Supabase Auth user."""
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
    "/{conversation_id}/sources",
    response_model=GetSourcesResponse,
)
async def get_sources(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> GetSourcesResponse:
    try:
        documents = await conversation_service.get_conversation_documents(
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
    conversation_service: ConversationServiceDep,
):
    try:
        deleted_document = await conversation_service.delete_document(
            conversation_id,
            document_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DeleteSourceResponse(deleted_document=deleted_document)


@conversation_router.patch("/{conversation_id}/sources/{document_id}")
async def change_source_name(
    conversation_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    name: str = Body(...),
):
    try:
        updated_name = await conversation_service.change_document_name(
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
    session: AsyncSession = Depends(get_session),
) -> SourceReportResponse:
    document_store = DocumentStore(session)
    try:
        report = await document_store.get_report(
            conversation_id,
            document_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return report_from_document_report(report)
