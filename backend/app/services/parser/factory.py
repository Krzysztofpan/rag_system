from fastapi import UploadFile

from app.services.parser.base import Parser
from app.services.parser.complex.parser import ComplexParser
from app.services.parser.simple import SimpleParser
from app.lib.file_types import FileTypes, resolve_file_type


class ParserFactory:
    @staticmethod
    def create_parser(file: UploadFile) -> Parser:
        content_type = resolve_file_type(file.content_type, file.filename)
        match content_type:
            case FileTypes.PDF | FileTypes.DOCX | FileTypes.PNG | FileTypes.JPEG:
                return ComplexParser(file)
            case FileTypes.MD | FileTypes.TXT:
                return SimpleParser(file)
            case _:
                raise ValueError(f"Unexpected file type: {content_type!r}")
