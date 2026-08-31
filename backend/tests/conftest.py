"""Pytest fixtures for the document indexing pipeline tests."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

# Keep SlowAPI on process-local memory so unit tests do not need Redis.
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"

from app.config import get_settings

get_settings.cache_clear()

import pytest
from fastapi import UploadFile

from app.lib.file_types import FileTypes
from tests.helpers import (
    FakeDocumentService,
    FakeVectorStore,
    make_upload_file,
)

@pytest.fixture
def conversation_id() -> UUID:
    return uuid4()


@pytest.fixture
def fake_document_service() -> FakeDocumentService:
    return FakeDocumentService()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def markdown_upload() -> UploadFile:
    return make_upload_file(
        "# Title\n\nHello world.\n\n## Section\n\nMore text about indexing.",
        content_type=FileTypes.MD,
        filename="note.md",
    )


@pytest.fixture
def text_upload() -> UploadFile:
    return make_upload_file(
        "Plain text paragraph one.\n\nPlain text paragraph two.",
        content_type=FileTypes.TXT,
        filename="note.txt",
    )


@pytest.fixture
def pdf_upload() -> UploadFile:
    return make_upload_file(
        b"%PDF-1.4 fake",
        content_type=FileTypes.PDF,
        filename="doc.pdf",
    )


@pytest.fixture
def docx_upload() -> UploadFile:
    return make_upload_file(
        b"PK\x03\x04fake-docx",
        content_type=FileTypes.DOCX,
        filename="doc.docx",
    )


@pytest.fixture
def png_upload() -> UploadFile:
    return make_upload_file(
        b"\x89PNG\r\n\x1a\n",
        content_type=FileTypes.PNG,
        filename="photo.png",
    )


@pytest.fixture
def jpeg_upload() -> UploadFile:
    return make_upload_file(
        b"\xff\xd8\xff",
        content_type=FileTypes.JPEG,
        filename="photo.jpg",
    )
