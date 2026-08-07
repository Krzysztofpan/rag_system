from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.session import get_session
from app.dependencies import CurrentUserDep
from app.schemas.conversation import (
    CreateConversationResponse,
    GetConversationsResponse,
    conversation_from_model,
)
from app.schemas.source import (
    DeleteSourceResponse,
    GetSourcesResponse,
    SourceReportResponse,
    report_from_document_report,
    source_from_document,
)
from app.services.conversation_store import ConversationStore
from app.services.doc_store import DocumentStore

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@conversation_router.post("/", response_model=CreateConversationResponse)
async def create_conversation(
    current_user: CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> CreateConversationResponse:
    """Create a conversation for the authenticated Supabase Auth user."""
    store = ConversationStore(session)
    try:
        conversation = await store.create_conversation(user_id=current_user.user_id)
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Unknown user") from exc
    return CreateConversationResponse(
        conversation_id=str(conversation.id),
        user_id=str(conversation.user_id),
    )

@conversation_router.get("/", response_model=GetConversationsResponse)
async def get_conversations(
    current_user: CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> GetConversationsResponse:
    conversation_store = ConversationStore(session)
    conversations = await conversation_store.get_conversations(user_id=current_user.user_id)

    return GetConversationsResponse(
        conversations=[conversation_from_model(c) for c in conversations],
    )



@conversation_router.get(
    "/{conversation_id}/sources",
    response_model=GetSourcesResponse,
)
async def get_sources(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> GetSourcesResponse:
    conversation_store = ConversationStore(session)
    try:
        documents = await conversation_store.get_conversation_documents(
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
    session: AsyncSession = Depends(get_session),
):
    document_store = DocumentStore(session)
    try:
        deleted_document = await document_store.delete_document(
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
    name: str = Body(...),
    session: AsyncSession = Depends(get_session),
):
    document_store = DocumentStore(session)
    try:
        updated_name = await document_store.change_document_name(
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
