from datetime import datetime
from typing import Any

from app.db.models import Resource, ResourceType
from app.schemas.base import APIModel


class ResourceResponse(APIModel):
    id: str
    type: ResourceType
    content: dict[str, Any]
    title: str
    created_at: datetime
    updated_at: datetime


class GetResourcesResponse(APIModel):
    count: int
    conversation_resources: list[ResourceResponse]


class CreateResourceRequest(APIModel):
    title: str
    content: dict[str, Any]


class CreateResourceResponse(APIModel):
    resource: ResourceResponse


def resource_from_model(resource: Resource) -> ResourceResponse:
    return ResourceResponse(
        id=str(resource.id),
        type=resource.type,
        content=resource.content,
        title=resource.title,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )
