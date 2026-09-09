from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.auth.deps import get_current_user
from app.db.models.resource import ResourceType
from app.dependencies import (
    CurrentUserDep,
    ResourceServiceDep,
    UsageLimitServiceDep,
)
from app.lib.note_markdown import DEFAULT_NOTE_TITLE
from app.schemas.resource import (
    ChatNoteContent,
    CreateNoteRequest,
    CreateResourceResponse,
    DeleteResourceResponse,
    GetResourcesResponse,
    UpdateNoteRequest,
    UserNoteContent,
    dump_note_content,
    resource_from_model,
)
from app.services.resource_service import ResourceNotEditableError
from app.services.usage_limits import LimitExceededError
from app.studio.note_title import apply_note_title

resource_router = APIRouter(
    prefix="/conversations/{conversation_id}/resources",
    tags=["resources"],
    dependencies=[Depends(get_current_user)],
)


def _http_limit(exc: LimitExceededError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.as_detail(),
    )


@resource_router.get(
    "",
    response_model=GetResourcesResponse,
)
async def get_resources(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    resource_service: ResourceServiceDep,
) -> GetResourcesResponse:
    try:
        resources = await resource_service.get_conversation_resources(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return GetResourcesResponse(
        count=len(resources),
        conversation_resources=[resource_from_model(r) for r in resources],
    )


@resource_router.post(
    "/note",
    response_model=CreateResourceResponse,
)
async def create_note_resource(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    resource_service: ResourceServiceDep,
    usage_limits: UsageLimitServiceDep,
    background_tasks: BackgroundTasks,
    body: CreateNoteRequest,
) -> CreateResourceResponse:
    note_content = body.content if body.content is not None else UserNoteContent()
    title = body.title.strip() if body.title else DEFAULT_NOTE_TITLE
    if not title:
        title = DEFAULT_NOTE_TITLE
    try:
        if isinstance(note_content, ChatNoteContent) and note_content.message_id is not None:
            existing = await resource_service.find_chat_note_by_message_id(
                conversation_id,
                note_content.message_id,
                user_id=current_user.user_id,
            )
            if existing is not None:
                return CreateResourceResponse(resource=resource_from_model(existing))

        if isinstance(note_content, ChatNoteContent):
            await usage_limits.enforce_create_chat_note(current_user.user_id)

        resource = await resource_service.create_resource(
            conversation_id,
            user_id=current_user.user_id,
            type=ResourceType.note,
            title=title,
            content=dump_note_content(note_content, by_alias=False),
        )
    except LimitExceededError as exc:
        raise _http_limit(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Title generation is only for chat pins, not user-created notes.
    if (
        isinstance(note_content, ChatNoteContent)
        and note_content.markdown.strip()
        and title == DEFAULT_NOTE_TITLE
    ):
        background_tasks.add_task(
            apply_note_title,
            conversation_id,
            resource.id,
            current_user.user_id,
        )

    return CreateResourceResponse(resource=resource_from_model(resource))


@resource_router.patch(
    "/note/{resource_id}",
    response_model=CreateResourceResponse,
)
async def update_note_resource(
    conversation_id: UUID,
    resource_id: UUID,
    current_user: CurrentUserDep,
    resource_service: ResourceServiceDep,
    body: UpdateNoteRequest,
) -> CreateResourceResponse:
    try:
        resource = await resource_service.update_note_content(
            conversation_id,
            resource_id,
            user_id=current_user.user_id,
            content=(
                dump_note_content(body.content, by_alias=False)
                if body.content is not None
                else None
            ),
            title=body.title,
        )
    except ResourceNotEditableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CreateResourceResponse(resource=resource_from_model(resource))


@resource_router.delete(
    "/{resource_id}",
    response_model=DeleteResourceResponse,
)
async def delete_resource(
    conversation_id: UUID,
    resource_id: UUID,
    current_user: CurrentUserDep,
    resource_service: ResourceServiceDep,
) -> DeleteResourceResponse:
    try:
        deleted_resource = await resource_service.delete_resource(
            conversation_id,
            resource_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DeleteResourceResponse(
        deleted_resource=resource_from_model(deleted_resource),
    )
