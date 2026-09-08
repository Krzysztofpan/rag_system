from typing import Annotated

from fastapi import Depends

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import (
    get_conversation_event_broker,
    get_conversation_memory_service,
    get_conversation_service,
    get_document_service,
    get_ingest_queue,
    get_message_service,
    get_resource_service,
    get_run_registry,
    get_usage_limit_service,
)
from app.ingest.queue import IngestQueue
from app.services.chat.redis_run_registry import RedisRunRegistry
from app.services.conversation_events import ConversationEventBroker
from app.services.conversation_service import ConversationService
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.document_service import DocumentService
from app.services.message_service import MessageService
from app.services.resource_service import ResourceService
from app.services.security import PromptGuardService, get_prompt_guard_service
from app.services.usage_limits import UsageLimitService

ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
ConversationMemoryServiceDep = Annotated[
    ConversationMemoryService, Depends(get_conversation_memory_service)
]
DocumentServiceDep = Annotated[
    DocumentService, Depends(get_document_service)
]
ResourceServiceDep = Annotated[
    ResourceService, Depends(get_resource_service)
]
MessageServiceDep = Annotated[
    MessageService, Depends(get_message_service)
]
UsageLimitServiceDep = Annotated[
    UsageLimitService, Depends(get_usage_limit_service)
]
PromptGuardServiceDep = Annotated[
    PromptGuardService, Depends(get_prompt_guard_service)
]
RedisRunRegistryDep = Annotated[
    RedisRunRegistry, Depends(get_run_registry)
]
ConversationEventBrokerDep = Annotated[
    ConversationEventBroker, Depends(get_conversation_event_broker)
]
IngestQueueDep = Annotated[IngestQueue, Depends(get_ingest_queue)]
CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]

__all__ = [
    "AuthenticatedUser",
    "ConversationEventBrokerDep",
    "ConversationServiceDep",
    "ConversationMemoryServiceDep",
    "CurrentUserDep",
    "DocumentServiceDep",
    "IngestQueueDep",
    "MessageServiceDep",
    "PromptGuardServiceDep",
    "RedisRunRegistryDep",
    "ResourceServiceDep",
    "UsageLimitServiceDep",
    "get_conversation_service",
    "get_current_user",
    "get_document_service",
    "get_resource_service",
    "get_usage_limit_service",
]
