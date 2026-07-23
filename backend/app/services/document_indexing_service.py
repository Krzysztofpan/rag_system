from fastapi import UploadFile

from app.services.parser import ParseResult, Parser


class DocumentIndexingService:
    def __init__(
        self,
        parser: Parser,
        doc_store=None,
        vector_store=None,
        embedder=None,
    ):
        self.doc_store = doc_store
        self.vector_store = vector_store
        self.embedder = embedder
        self.parser = parser

    async def ingest(self, file: UploadFile) -> ParseResult:
        return await self.parser._parse()
