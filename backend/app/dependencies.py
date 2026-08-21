from typing import Annotated

from fastapi import Depends

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import (
    get_conversation_memory_service,
    get_conversation_service,
    get_document_indexing_service,
    get_document_service,
    get_message_service,
    get_run_registry,
)
from app.services.chat.run_registry import InMemoryRunRegistry
from app.services.conversation_service import ConversationService
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_service import DocumentService
from app.services.message_service import MessageService

DocumentIndexingServiceDep = Annotated[
    DocumentIndexingService, Depends(get_document_indexing_service)
]
ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
ConversationMemoryServiceDep = Annotated[
    ConversationMemoryService, Depends(get_conversation_memory_service)
]
DocumentServiceDep = Annotated[
    DocumentService, Depends(get_document_service)
]
MessageServiceDep = Annotated[
    MessageService, Depends(get_message_service)
]
RunRegistryDep = Annotated[
    InMemoryRunRegistry, Depends(get_run_registry)
]
CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]

__all__ = [
    "AuthenticatedUser",
    "ConversationServiceDep",
    "ConversationMemoryServiceDep",
    "CurrentUserDep",
    "DocumentIndexingServiceDep",
    "DocumentServiceDep",
    "MessageServiceDep",
    "RunRegistryDep",
    "get_conversation_service",
    "get_current_user",
    "get_document_indexing_service",
    "get_document_service",
]
