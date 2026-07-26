from fastapi import UploadFile

from app.services.parser.base import Parser
from app.services.parser.complex.parser import ComplexParser
from app.services.parser.simple import SimpleParser
from app.types import FileTypes


class ParserFactory:
    @staticmethod
    def create_parser(file: UploadFile) -> Parser:
        content_type = file.content_type or ""
        match content_type:
            case FileTypes.PDF | FileTypes.DOCX:
                return ComplexParser(file)
            case FileTypes.MD | FileTypes.TXT:
                return SimpleParser(file)
            case _:
                raise ValueError(f"Unexpected file type: {content_type!r}")
