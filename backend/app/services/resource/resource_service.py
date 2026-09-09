from datetime import UTC, datetime
from typing import Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Resource
from app.db.models.conversation import Conversation
from app.db.models.resource import ResourceType
from app.lib.note_markdown import DEFAULT_NOTE_TITLE, note_source_markdown, source_filename_from_title
from app.prompts.resource import NOTE_TITLE_MAX_CHARS


class ResourceNotEditableError(ValueError):
    """Raised when a resource exists but cannot be updated as a user note."""


class ResourceNotConvertibleError(ValueError):
    """Raised when a resource cannot be ingested as a source."""


class ResourceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_conversation_resources(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> List[Resource]:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        resources_result = await self.session.execute(
            select(Resource).where(Resource.conversation_id == conversation_id)
        )
        return list(resources_result.scalars().all())

    async def create_resource(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
        type: ResourceType,
        title: str,
        content: dict[str, Any],
    ) -> Resource:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )

        if result.scalar_one_or_none() is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        resource = Resource(
            conversation_id=conversation_id,
            type=type,
            title=title,
            content=content,
        )
        self.session.add(resource)
        await self.session.commit()
        return resource

    async def find_chat_note_by_message_id(
        self,
        conversation_id: UUID,
        message_id: UUID,
        *,
        user_id: UUID,
    ) -> Resource | None:
        result = await self.session.execute(
            select(Resource)
            .join(Conversation, Conversation.id == Resource.conversation_id)
            .where(
                Resource.conversation_id == conversation_id,
                Conversation.user_id == user_id,
                Resource.type == ResourceType.note,
                Resource.content["kind"].astext == "chat",
                Resource.content["message_id"].astext == str(message_id),
            )
        )
        return result.scalar_one_or_none()

    async def get_resource(
        self,
        conversation_id: UUID,
        resource_id: UUID,
        *,
        user_id: UUID,
    ) -> Resource:
        result = await self.session.execute(
            select(Resource)
            .join(Conversation, Conversation.id == Resource.conversation_id)
            .where(
                Resource.id == resource_id,
                Resource.conversation_id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        resource = result.scalar_one_or_none()
        if resource is None:
            raise ValueError(f"Resource {resource_id} not found")
        return resource

    async def delete_resource(
        self,
        conversation_id: UUID,
        resource_id: UUID,
        *,
        user_id: UUID,
    ) -> Resource:
        resource = await self.get_resource(
            conversation_id,
            resource_id,
            user_id=user_id,
        )
        await self.session.delete(resource)
        await self.session.commit()
        return resource

    async def update_note_content(
        self,
        conversation_id: UUID,
        resource_id: UUID,
        *,
        user_id: UUID,
        content: dict[str, Any] | None = None,
        title: str | None = None,
    ) -> Resource:
        resource = await self.get_resource(
            conversation_id,
            resource_id,
            user_id=user_id,
        )
        if resource.type != ResourceType.note:
            raise ResourceNotEditableError("Only notes can be updated")

        kind = (resource.content or {}).get("kind", "user")
        if content is not None:
            if kind == "chat":
                raise ResourceNotEditableError("Chat note content cannot be updated")
            resource.content = content
            flag_modified(resource, "content")
        if title is not None:
            next_title = title.strip() or DEFAULT_NOTE_TITLE
            resource.title = next_title[:NOTE_TITLE_MAX_CHARS].rstrip()
        resource.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def update_title(
        self,
        conversation_id: UUID,
        resource_id: UUID,
        *,
        user_id: UUID,
        title: str,
    ) -> Resource:
        resource = await self.get_resource(
            conversation_id,
            resource_id,
            user_id=user_id,
        )
        if not title:
            raise ValueError("You have to define new title.")
        if resource.title != DEFAULT_NOTE_TITLE:
            return resource

        resource.title = title
        resource.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def get_note_source_payload(
        self,
        conversation_id: UUID,
        resource_id: UUID,
        *,
        user_id: UUID,
    ) -> tuple[str, str]:
        resource = await self.get_resource(
            conversation_id,
            resource_id,
            user_id=user_id,
        )
        if resource.type != ResourceType.note:
            raise ResourceNotConvertibleError("Only notes can be converted to sources")

        markdown = note_source_markdown(resource.title, resource.content)
        if not markdown:
            raise ResourceNotConvertibleError("Note has no content")

        return source_filename_from_title(resource.title), markdown
