from enum import Enum


class FileTypes(str, Enum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MD = "text/markdown"
    TXT = "text/plain"
