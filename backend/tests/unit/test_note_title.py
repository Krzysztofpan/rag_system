from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.db.models.resource import Resource, ResourceType
from app.lib.note_markdown import DEFAULT_NOTE_TITLE
from app.prompts import NOTE_TITLE_CONTENT_CHAR_LIMIT
from app.studio.note_title import NoteTitle, apply_note_title, generate_note_title


def _session_factory(resource: Resource | None = None):
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=session_cm), session, resource


async def test_generate_note_title_uses_structured_output():
    chain = MagicMock()
    chain.__or__.return_value = chain
    chain.ainvoke = AsyncMock(return_value=NoteTitle(title="Invoice terms"))

    with (
        patch(
            "app.studio.note_title.ChatPromptTemplate.from_template",
            return_value=chain,
        ),
        patch("app.studio.note_title.ChatOpenAI"),
    ):
        title = await generate_note_title("A long assistant message about invoices.")

    chain.ainvoke.assert_awaited_once_with(
        {"note_content": "A long assistant message about invoices."},
        config={"run_name": "generate_note_title"},
    )
    assert title == "Invoice terms"


async def test_generate_note_title_truncates_long_content():
    chain = MagicMock()
    chain.__or__.return_value = chain
    chain.ainvoke = AsyncMock(return_value=NoteTitle(title="Invoices"))

    with (
        patch(
            "app.studio.note_title.ChatPromptTemplate.from_template",
            return_value=chain,
        ),
        patch("app.studio.note_title.ChatOpenAI"),
    ):
        await generate_note_title("x" * 2000)

    chain.ainvoke.assert_awaited_once_with(
        {"note_content": "x" * NOTE_TITLE_CONTENT_CHAR_LIMIT},
        config={"run_name": "generate_note_title"},
    )


async def test_apply_note_title_updates_and_publishes():
    conversation_id = uuid4()
    user_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title=DEFAULT_NOTE_TITLE,
        content={"kind": "chat", "markdown": "Hello about contracts"},
    )
    session_factory, _session, _ = _session_factory(resource)
    service = MagicMock()
    service.get_resource = AsyncMock(return_value=resource)
    updated = Resource(
        id=resource.id,
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="Contract recap",
        content=resource.content,
    )
    service.update_title = AsyncMock(return_value=updated)
    broker = MagicMock()
    broker.publish = AsyncMock()

    with (
        patch(
            "app.studio.note_title.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.studio.note_title.ResourceService",
            return_value=service,
        ),
        patch(
            "app.studio.note_title.generate_note_title",
            new=AsyncMock(return_value="Contract recap"),
        ),
        patch(
            "app.studio.note_title.get_conversation_event_broker",
            return_value=broker,
        ),
    ):
        await apply_note_title(conversation_id, resource.id, user_id)

    service.update_title.assert_awaited_once_with(
        conversation_id,
        resource.id,
        user_id=user_id,
        title="Contract recap",
    )
    broker.publish.assert_awaited_once_with(
        conversation_id,
        {
            "event": "resource.updated",
            "conversationId": str(conversation_id),
            "resourceId": str(resource.id),
            "title": "Contract recap",
        },
    )


async def test_apply_note_title_skips_missing_resource():
    conversation_id = uuid4()
    resource_id = uuid4()
    user_id = uuid4()
    session_factory, _session, _ = _session_factory()
    service = MagicMock()
    service.get_resource = AsyncMock(side_effect=ValueError("gone"))
    broker = MagicMock()
    broker.publish = AsyncMock()

    with (
        patch(
            "app.studio.note_title.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.studio.note_title.ResourceService",
            return_value=service,
        ),
        patch(
            "app.studio.note_title.generate_note_title",
            new=AsyncMock(),
        ) as generate,
        patch(
            "app.studio.note_title.get_conversation_event_broker",
            return_value=broker,
        ),
    ):
        await apply_note_title(conversation_id, resource_id, user_id)

    generate.assert_not_awaited()
    broker.publish.assert_not_awaited()


async def test_apply_note_title_skips_user_notes():
    conversation_id = uuid4()
    user_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title=DEFAULT_NOTE_TITLE,
        content={"kind": "user", "html": "<p>Hi</p>"},
    )
    session_factory, _session, _ = _session_factory(resource)
    service = MagicMock()
    service.get_resource = AsyncMock(return_value=resource)
    broker = MagicMock()
    broker.publish = AsyncMock()

    with (
        patch(
            "app.studio.note_title.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.studio.note_title.ResourceService",
            return_value=service,
        ),
        patch(
            "app.studio.note_title.generate_note_title",
            new=AsyncMock(),
        ) as generate,
        patch(
            "app.studio.note_title.get_conversation_event_broker",
            return_value=broker,
        ),
    ):
        await apply_note_title(conversation_id, resource.id, user_id)

    generate.assert_not_awaited()
    service.update_title.assert_not_called()
    broker.publish.assert_not_awaited()


async def test_apply_note_title_swallows_generation_errors():
    with patch(
        "app.studio.note_title._apply_note_title",
        new=AsyncMock(side_effect=RuntimeError("llm down")),
    ):
        await apply_note_title(uuid4(), uuid4(), uuid4())
