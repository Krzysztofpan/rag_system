from app.services.chunker.base import Chunker
from app.services.chunker.complex import ComplexChunker
from app.services.chunker.simple import SimpleChunker
from app.lib.file_types import FileTypes, resolve_file_type


class ChunkerFactory:
    @staticmethod
    def create_chunker(
        content_type: str | FileTypes | None,
        filename: str | None = None,
    ) -> Chunker:
        resolved = resolve_file_type(content_type, filename)
        match resolved:
            case FileTypes.PDF | FileTypes.DOCX | FileTypes.PNG | FileTypes.JPEG:
                return ComplexChunker(resolved)
            case FileTypes.MD | FileTypes.TXT:
                return SimpleChunker(resolved)
            case _:
                raise ValueError(f"Unexpected file type: {content_type!r}")
