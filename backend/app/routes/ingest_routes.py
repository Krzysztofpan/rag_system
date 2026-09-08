from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)

from app.auth.deps import get_current_user
from app.dependencies import (
    ConversationServiceDep,
    CurrentUserDep,
    DocumentServiceDep,
    IngestQueueDep,
    ResourceServiceDep,
    UsageLimitServiceDep,
)
from app.ingest.queue import DocumentIngestJob, YoutubeIngestJob
from app.lib.file_types import FileTypes, resolve_document_file_type
from app.lib.rate_limit import ingest_error_message, ingest_limit_value, limiter
from app.lib.upload_temp import UploadTooLargeError, save_bytes_to_temp, save_upload_to_temp
from app.lib.youtube_url import InvalidYoutubeUrlError, parse_youtube_url
from app.schemas.origin import FileOrigin, YoutubeOrigin
from app.schemas.source import IngestUrlRequest, SourceResponse, source_from_document
from app.services.resource_service import ResourceNotConvertibleError
from app.services.usage_limits import LimitCode, LimitExceededError

ingest_router = APIRouter(
    prefix="/ingest",
    tags=["ingest"],
    dependencies=[Depends(get_current_user)],
)


def _http_limit(exc: LimitExceededError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.as_detail(),
    )


@ingest_router.post(
    "/{conversation_id}/url",
    response_model=SourceResponse,
    status_code=202,
)
@limiter.shared_limit(
    ingest_limit_value,
    scope="ingest",
    error_message=ingest_error_message,
)
async def ingest_source_url(
    request: Request,
    response: Response,
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    document_service: DocumentServiceDep,
    ingest_queue: IngestQueueDep,
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
    document = await document_service.mark_processing(document.id)
    await ingest_queue.enqueue(
        YoutubeIngestJob(
            conversation_id=conversation_id,
            document_id=document.id,
            user_id=current_user.user_id,
            url=video.url,
            video_id=video.video_id,
        )
    )
    return source_from_document(document)


@ingest_router.post(
    "/{conversation_id}/document",
    response_model=SourceResponse,
    status_code=202,
)
@limiter.shared_limit(
    ingest_limit_value,
    scope="ingest",
    error_message=ingest_error_message,
)
async def ingest_source_document(
    request: Request,
    response: Response,
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    document_service: DocumentServiceDep,
    usage_limits: UsageLimitServiceDep,
    ingest_queue: IngestQueueDep,
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
    try:
        path, size = await save_upload_to_temp(
            file,
            max_bytes=(
                usage_limits.settings.max_upload_bytes
                if usage_limits.enabled
                else None
            ),
        )
    except UploadTooLargeError as exc:
        raise _http_limit(
            LimitExceededError(
                LimitCode.max_upload_bytes,
                limit=usage_limits.settings.max_upload_bytes,
                current=exc.size,
                message=f"File exceeds the {usage_limits.settings.max_upload_bytes} byte upload limit.",
            )
        ) from exc
    try:
        document = await document_service.create_document(
            conversation_id=conversation_id,
            filename=filename,
            content_type=content_type,
            origin=FileOrigin(file_size_bytes=size),
        )
        document = await document_service.mark_processing(document.id)
        await ingest_queue.enqueue(
            DocumentIngestJob(
                conversation_id=conversation_id,
                document_id=document.id,
                user_id=current_user.user_id,
                path=str(path),
                filename=filename,
                content_type=content_type,
            )
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise

    return source_from_document(document)


@ingest_router.post(
    "/{conversation_id}/note/{resource_id}",
    response_model=SourceResponse,
    status_code=202,
)
@limiter.shared_limit(
    ingest_limit_value,
    scope="ingest",
    error_message=ingest_error_message,
)
async def ingest_note_resource(
    request: Request,
    response: Response,
    conversation_id: UUID,
    resource_id: UUID,
    current_user: CurrentUserDep,
    resource_service: ResourceServiceDep,
    document_service: DocumentServiceDep,
    usage_limits: UsageLimitServiceDep,
    ingest_queue: IngestQueueDep,
) -> SourceResponse:
    try:
        filename, markdown = await resource_service.get_note_source_payload(
            conversation_id,
            resource_id,
            user_id=current_user.user_id,
        )
    except ResourceNotConvertibleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        path, size = save_bytes_to_temp(
            markdown.encode("utf-8"),
            suffix=".md",
            max_bytes=(
                usage_limits.settings.max_upload_bytes
                if usage_limits.enabled
                else None
            ),
        )
    except UploadTooLargeError as exc:
        raise _http_limit(
            LimitExceededError(
                LimitCode.max_upload_bytes,
                limit=usage_limits.settings.max_upload_bytes,
                current=exc.size,
                message=f"File exceeds the {usage_limits.settings.max_upload_bytes} byte upload limit.",
            )
        ) from exc

    try:
        document = await document_service.create_document(
            conversation_id=conversation_id,
            filename=filename,
            content_type=FileTypes.MD,
            origin=FileOrigin(file_size_bytes=size),
        )
        document = await document_service.mark_processing(document.id)
        await ingest_queue.enqueue(
            DocumentIngestJob(
                conversation_id=conversation_id,
                document_id=document.id,
                user_id=current_user.user_id,
                path=str(path),
                filename=filename,
                content_type=FileTypes.MD,
            )
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise

    return source_from_document(document)
