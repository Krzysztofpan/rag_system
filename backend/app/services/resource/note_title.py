from __future__ import annotations

import logging
from uuid import UUID

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.container import get_conversation_event_broker
from app.db.models.resource import ResourceType
from app.db.session import get_session_factory
from app.lib.note_markdown import DEFAULT_NOTE_TITLE, note_body_text
from app.lib.tracing import conversation_tracing
from app.prompts import (
    NOTE_TITLE_CONTENT_CHAR_LIMIT,
    NOTE_TITLE_MAX_CHARS,
    NOTE_TITLE_TEMPLATE,
)
from app.schemas.resource import ChatNoteContent, parse_note_content
from app.services.conversation.conversation_events import resource_updated_event
from app.services.resource.resource_service import ResourceService

logger = logging.getLogger(__name__)


class NoteTitle(BaseModel):
    title: str = Field(
        description="Note title. A few words, not a sentence.",
        max_length=NOTE_TITLE_MAX_CHARS,
    )


async def generate_note_title(note_content: str) -> str:
    prompt = ChatPromptTemplate.from_template(NOTE_TITLE_TEMPLATE)
    title_llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=40).with_structured_output(
        NoteTitle
    )
    title_chain = prompt | title_llm
    result = await title_chain.ainvoke(
        {"note_content": note_content[:NOTE_TITLE_CONTENT_CHAR_LIMIT]},
        config={"run_name": "generate_note_title"},
    )
    title = result.title.strip()
    if not title:
        raise ValueError("You have to define new title.")
    return title[:NOTE_TITLE_MAX_CHARS].rstrip()


async def apply_note_title(
    conversation_id: UUID,
    resource_id: UUID,
    user_id: UUID,
) -> None:
    try:
        await _apply_note_title(conversation_id, resource_id, user_id)
    except Exception:
        logger.exception(
            "note title generation failed",
            extra={"resource_id": str(resource_id)},
        )


async def _apply_note_title(
    conversation_id: UUID,
    resource_id: UUID,
    user_id: UUID,
) -> None:
    with conversation_tracing(
        conversation_id,
        user_id=user_id,
        tags=["studio"],
        extra_metadata={"resource_id": resource_id},
    ):
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = ResourceService(session)
            try:
                resource = await service.get_resource(
                    conversation_id,
                    resource_id,
                    user_id=user_id,
                )
            except ValueError:
                logger.info(
                    "note title skipped; resource %s is gone",
                    resource_id,
                )
                return

            if resource.type != ResourceType.note:
                return
            if resource.title != DEFAULT_NOTE_TITLE:
                return
            parsed = parse_note_content(resource.content)
            if not isinstance(parsed, ChatNoteContent):
                return
            body = note_body_text(resource.content)
            if not body:
                return

        title = await generate_note_title(body)

        async with session_factory() as session:
            service = ResourceService(session)
            try:
                resource = await service.update_title(
                    conversation_id,
                    resource_id,
                    user_id=user_id,
                    title=title,
                )
            except ValueError:
                logger.info(
                    "note title skipped; resource %s is gone",
                    resource_id,
                )
                return

        await get_conversation_event_broker().publish(
            conversation_id,
            resource_updated_event(
                conversation_id,
                resource.id,
                resource.title,
            ),
        )
