from fastapi import UploadFile

from app.services.parser.base import FileTypes, Parser
from app.services.parser.complex.parser import ComplexParser
from app.services.parser.simple import SimpleParser


class ParserFactory:
    def __init__(self, file: UploadFile):
        self.file = file

    def create_parser(self) -> Parser:
        content_type = self.file.content_type or ""
        match content_type:
            case FileTypes.PDF | FileTypes.DOCX:
                return ComplexParser(self.file)
            case FileTypes.MD | FileTypes.TXT:
                return SimpleParser(self.file)
            case _:
                raise ValueError(f"Unexpected file type: {content_type!r}")
