from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resource import ResourceType
from app.db.models import Resource
from app.db.models.conversation import Conversation


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
        content: str,
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