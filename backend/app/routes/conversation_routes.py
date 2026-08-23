from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from fastapi import Query
from app.schemas.message import GetConversationMessagesResponse

from app.auth.deps import get_current_user
from app.background_tasks.document_background import ingest_document_source
from app.background_tasks.youtube_background import ingest_youtube_source
from app.dependencies import (
    ConversationServiceDep,
    CurrentUserDep,
    DocumentServiceDep,
    MessageServiceDep
)
from app.db.models.document import DocumentStatus
from app.lib.file_types import FileTypes, resolve_document_file_type
from app.lib.upload_temp import save_upload_to_temp
from app.lib.youtube_url import InvalidYoutubeUrlError, parse_youtube_url
from app.schemas.origin import FileOrigin, YoutubeOrigin
from app.schemas.conversation import (
    CreateConversationResponse,
    GetConversationsResponse,
    conversation_from_model,
    DeleteConversationResponse
)
from app.schemas.source import (
    DeleteSourceResponse,
    GetSourcesResponse,
    IngestUrlRequest,
    SourceReportResponse,
    SourceResponse,
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
        has_more=message_page.has_more
    )
   

@conversation_router.post(
    "/{conversation_id}/sources/url",
    response_model=SourceResponse,
    status_code=202,
)
async def ingest_source_url(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    document_service: DocumentServiceDep,
    background_tasks: BackgroundTasks,
    body: IngestUrlRequest,
) -> SourceResponse:
    try:
        video = parse_youtube_url(body.url)
    except InvalidYoutubeUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    document = await document_service.create_document(
        conversation_id=conversation_id,
        filename=f"youtube:{video.video_id}",
        content_type=FileTypes.YOUTUBE,
        origin=YoutubeOrigin(video_id=video.video_id, url=video.url),
    )
    await document_service.mark_processing(document.id)
    document.status = DocumentStatus.processing

    background_tasks.add_task(
        ingest_youtube_source,
        conversation_id,
        document.id,
        current_user.user_id,
        video.url,
        video.video_id,
    )
    return source_from_document(document)


@conversation_router.post(
    "/{conversation_id}/sources/document",
    response_model=SourceResponse,
    status_code=202,
)
async def ingest_source_document(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    document_service: DocumentServiceDep,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> SourceResponse:
    try:
        resolve_document_file_type(file.content_type, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filename = file.filename or "unknown"
    content_type = file.content_type
    path, size = await save_upload_to_temp(file)
    try:
        document = await document_service.create_document(
            conversation_id=conversation_id,
            filename=filename,
            content_type=content_type,
            origin=FileOrigin(file_size_bytes=size),
        )
        await document_service.mark_processing(document.id)
        document.status = DocumentStatus.processing

        background_tasks.add_task(
            ingest_document_source,
            conversation_id,
            document.id,
            current_user.user_id,
            str(path),
            filename,
            content_type,
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise

    return source_from_document(document)


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
):
    try:
        deleted_document = await document_service.delete_document(
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
