from app.services.chunker.base import Chunker
from app.services.chunker.complex import ComplexChunker
from app.services.chunker.simple import SimpleChunker
from app.types import FileTypes


class ChunkerFactory:
    @staticmethod
    def create_chunker(content_type: FileTypes) -> Chunker:
        match content_type:
            case FileTypes.PDF | FileTypes.DOCX:
                return ComplexChunker(content_type)
            case FileTypes.MD | FileTypes.TXT:
                return SimpleChunker(content_type)
            case _:
                raise ValueError(f"Unexpected file type: {content_type!r}")
