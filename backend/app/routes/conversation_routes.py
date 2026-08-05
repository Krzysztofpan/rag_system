from fastapi import Depends,HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.session import get_session

from app.schemas.conversation import (
    CreateConversationRequest,
    CreateConversationResponse,
)
from app.schemas.resource import (
    GetResourcesResponse,
    ResourceReportResponse,
    DeleteResourceResponse,
    report_from_document_report,
    resource_from_document,
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
    "/{conversation_id}/resources",
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

@conversation_router.delete(
    "/{conversation_id}/resources/{document_id}"
)
async def delete_resource(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    document_store = DocumentStore(session)
    try:
        deleted_document = await document_store.delete_document(conversation_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) 
    
    return DeleteResourceResponse(
        deleted_document=deleted_document
    )

@conversation_router.patch(
    "/{conversation_id}/resources/{document_id}"
)
async def change_resource_name(
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
    "/{conversation_id}/resources/{document_id}/report",
    response_model=ResourceReportResponse,
)
async def get_resource_report(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ResourceReportResponse:
    document_store = DocumentStore(session)
    try:
        report = await document_store.get_report(conversation_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return report_from_document_report(report)