from fastapi import UploadFile

from app.services.chunker import ChunkResult, Chunker
from app.services.parser import Parser


class DocumentIndexingService:
    def __init__(
        self,
        parser: Parser,
        chunker: Chunker,
        doc_store=None,
        vector_store=None,
        embedder=None,
    ):
        self.doc_store = doc_store
        self.vector_store = vector_store
        self.embedder = embedder
        self.parser = parser
        self.chunker = chunker

    async def ingest(self, file: UploadFile) -> list[ChunkResult]:
        res = await self.parser._parse()
        doc = res.document if res.document is not None else res.markdown
        return self.chunker._chunk(doc=doc, source_text=res.markdown)
