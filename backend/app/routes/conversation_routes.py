from fastapi import Depends,HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.session import get_session

from app.schemas.conversation import (
    CreateConversationRequest,
    CreateConversationResponse,
)
from app.schemas.source import (
    GetSourcesResponse,
    SourceReportResponse,
    DeleteSourceResponse,
    report_from_document_report,
    source_from_document,
)

from app.services.conversation_store import ConversationStore
from app.services.doc_store import DocumentStore
from fastapi import APIRouter

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)

@conversation_router.post("/", response_model=CreateConversationResponse)
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


@conversation_router.get(
    "/{conversation_id}/sources",
    response_model=GetSourcesResponse,
)
async def get_sources(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> GetSourcesResponse:
    conversation_store = ConversationStore(session)

    conversation_documents = await conversation_store.get_conversation_documents(
        conversation_id
    )
    sources = [source_from_document(document) for document in conversation_documents]

    return GetSourcesResponse(
        count=len(sources),
        conversation_sources=sources,
    )

@conversation_router.delete(
    "/{conversation_id}/sources/{document_id}"
)
async def delete_source(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    document_store = DocumentStore(session)
    try:
        deleted_document = await document_store.delete_document(conversation_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) 
    
    return DeleteSourceResponse(
        deleted_document=deleted_document
    )

@conversation_router.patch(
    "/{conversation_id}/sources/{document_id}"
)
async def change_source_name(
    conversation_id: UUID,
    document_id: UUID,
    name: str,
    session: AsyncSession = Depends(get_session),
):
    document_store = DocumentStore(session)
    try:
        updated_name = await document_store.change_document_name(conversation_id, document_id, name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) 
    
    return updated_name



@conversation_router.get(
    "/{conversation_id}/sources/{document_id}/report",
    response_model=SourceReportResponse,
)
async def get_source_report(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SourceReportResponse:
    document_store = DocumentStore(session)
    try:
        report = await document_store.get_report(conversation_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return report_from_document_report(report)
