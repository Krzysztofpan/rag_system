from app.services.chunker.base import ChunkResult, Chunker
from app.types import FileTypes
from langchain_text_splitters import RecursiveCharacterTextSplitter

_MARKDOWN_SEPARATORS = [
    "\n## ",
    "\n### ",
    "\n#### ",
    "\n# ",
    "\n\n",
    "\n",
    " ",
    "",
]

_PLAIN_SEPARATORS = [
    "\n\n",
    "\n",
    " ",
    "",
]


class SimpleChunker(Chunker):

    def __init__(self, content_type):
        super().__init__(content_type)

        separators = (
            _MARKDOWN_SEPARATORS
            if content_type in (FileTypes.MD, FileTypes.TXT)
            else _PLAIN_SEPARATORS
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.embedding_model_max_tokens,
            chunk_overlap=self.embedding_model_max_tokens // 10,
            separators=separators,
            keep_separator="start",
            add_start_index=True,
            length_function=self.count_tokens,
        )

    def _chunk(self, *, doc: str, source_text: str) -> list[ChunkResult]:
        results: list[ChunkResult] = []
        for piece in self.text_splitter.create_documents([doc]):
            content = piece.page_content
            char_start = piece.metadata["start_index"]
            results.append(
                ChunkResult(
                    content=content,
                    context=None,
                    char_start=char_start,
                    char_end=char_start + len(content),
                    token_count=self.count_tokens(content),
                )
            )
        return results
