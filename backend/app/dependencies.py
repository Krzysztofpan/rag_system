from typing import Annotated

from fastapi import Depends

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import (
    get_conversation_service,
    get_document_indexing_service,
    get_document_service,
)
from app.services.conversation_service import ConversationService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_service import DocumentService
from app.services.message_service import MessageService
from app.container import get_message_service

DocumentIndexingServiceDep = Annotated[
    DocumentIndexingService, Depends(get_document_indexing_service)
]
ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
DocumentServiceDep = Annotated[
    DocumentService, Depends(get_document_service)
]
MessageServiceDep = Annotated[
    MessageService, Depends(get_message_service)
]
CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]

__all__ = [
    "AuthenticatedUser",
    "ConversationServiceDep",
    "CurrentUserDep",
    "DocumentIndexingServiceDep",
    "DocumentServiceDep",
    "get_conversation_service",
    "get_current_user",
    "get_document_indexing_service",
    "get_document_service",
]
