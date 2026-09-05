from app.db.models import  Resource
from app.schemas.base import APIModel

class GetResourcesResponse(APIModel):
    count: int
    conversation_resources: list[Resource]

class CreateResourceRequest(APIModel):
    title: str
    content: str

class CreateResourceResponse(APIModel):
    resource: Resource