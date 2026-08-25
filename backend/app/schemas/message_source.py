from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.alias_generators import to_camel


class MessageSourceBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    index: int = Field(ge=1)


class ChunkMessageSource(MessageSourceBase):
    kind: Literal["chunk"] = "chunk"
    chunk_id: UUID


class SummaryMessageSource(MessageSourceBase):
    kind: Literal["summary"] = "summary"
    document_id: UUID


class WebMessageSource(MessageSourceBase):
    kind: Literal["web"] = "web"
    url: str
    title: str = ""


MessageSource = Annotated[
    ChunkMessageSource | SummaryMessageSource | WebMessageSource,
    Field(discriminator="kind"),
]

_message_source_adapter = TypeAdapter(MessageSource)


def dump_message_sources(
    items: Sequence[object] | None,
    *,
    by_alias: bool = False,
) -> list[dict[str, object]]:
    """Validate and serialize source pointers for storage or the API."""
    return [
        _message_source_adapter.validate_python(item).model_dump(
            mode="json",
            by_alias=by_alias,
        )
        for item in items or []
    ]
