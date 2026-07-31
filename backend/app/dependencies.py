from app.services.document_indexing_service import DocumentIndexingService
from typing import Annotated
from fastapi import Depends
from app.container import get_document_indexing_service

DocumentIndexingServiceDep = Annotated[DocumentIndexingService, Depends(get_document_indexing_service)]

__all__ = ["DocumentIndexingServiceDep", "get_document_indexing_service"]