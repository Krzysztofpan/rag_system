from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import Settings
from app.db.models.conversation import Conversation
from app.db.models.conversation_summary import ConversationSummary
from app.db.models.message import Message, MessageRole
from app.schemas.conversation_memory import ConversationMemorySummary
from app.services.conversation_memory_service import ConversationMemoryService


def _message(conversation_id, role, text):
    return Message(
        conversation_id=conversation_id,
        role=role,
        text=text,
    )


async def test_build_context_for_agent_includes_summary_history_and_current():
    conversation_id = uuid4()
    user_id = uuid4()
    session = AsyncMock()
    conversation_service = AsyncMock()
    message_service = AsyncMock()
    compactor = AsyncMock()
    service = ConversationMemoryService(
        session=session,
        conversation_service=conversation_service,
        message_service=message_service,
        settings=Settings(
            memory_enabled=True,
            memory_compaction_max_messages=12,
        ),
        compactor=compactor,
    )
    conversation = Conversation(
        id=conversation_id,
        user_id=user_id,
    )
    service._get_summary_state = AsyncMock(
        return_value=ConversationSummary(
            conversation_id=conversation_id,
            messages_summary={
                "goals_and_topics": ["compare contracts"],
                "established_facts": [],
                "user_preferences": ["short answers"],
                "open_questions": [],
            },
        )
    )
    message_service.get_messages_after.return_value = [
        _message(conversation_id, MessageRole.user, "Previous question"),
        _message(conversation_id, MessageRole.assistant, "Previous answer"),
        _message(conversation_id, MessageRole.user, "Follow-up"),
    ]

    messages = await service.build_context_for_agent(
        conversation,
    )

    assert [type(message) for message in messages] == [
        SystemMessage,
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert messages[-1].content == "Follow-up"
    assert sum(message.content == "Follow-up" for message in messages) == 1
    message_service.get_messages_after.assert_awaited_once_with(
        conversation_id,
        user_id=user_id,
        after_id=None,
        limit=12,
        newest_first=True,
    )


async def test_memory_can_be_disabled():
    conversation = Conversation(id=uuid4(), user_id=uuid4())
    message_service = AsyncMock()
    message_service.get_messages_after.return_value = [
        _message(conversation.id, MessageRole.user, "Only this turn")
    ]
    service = ConversationMemoryService(
        session=AsyncMock(),
        conversation_service=AsyncMock(),
        message_service=message_service,
        settings=Settings(memory_enabled=False),
        compactor=AsyncMock(),
    )
    service._get_summary_state = AsyncMock(return_value=None)

    messages = await service.build_context_for_agent(conversation)

    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    message_service.get_messages_after.assert_awaited_once_with(
        conversation.id,
        user_id=conversation.user_id,
        after_id=None,
        limit=1,
        newest_first=True,
    )


async def test_compaction_keeps_recent_messages_and_advances_watermark():
    conversation_id = uuid4()
    user_id = uuid4()
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(rowcount=1)
    conversation_service = AsyncMock()
    message_service = AsyncMock()
    compactor = AsyncMock()
    settings = Settings(
        memory_enabled=True,
        memory_compaction_max_messages=6,
        memory_compaction_max_tokens=100_000,
        memory_keep_recent_messages=2,
    )
    service = ConversationMemoryService(
        session=session,
        conversation_service=conversation_service,
        message_service=message_service,
        settings=settings,
        compactor=compactor,
    )
    conversation_service.get_conversation.return_value = Conversation(
        id=conversation_id,
        user_id=user_id,
    )
    service._get_summary_state = AsyncMock(
        return_value=ConversationSummary(
            conversation_id=conversation_id,
            messages_summary={
                "goals_and_topics": [],
                "established_facts": [],
                "user_preferences": [],
                "open_questions": [],
            },
            version=3,
        )
    )
    db_messages = [
        _message(
            conversation_id,
            MessageRole.user if index % 2 == 0 else MessageRole.assistant,
            f"turn {index}",
        )
        for index in range(6)
    ]
    message_service.get_messages_after.return_value = db_messages
    summary = ConversationMemorySummary(goals_and_topics=["goal"])
    compactor.merge.return_value = summary

    compacted = await service.compact_if_needed(
        conversation_id,
        user_id=user_id,
    )

    assert compacted is True
    turns = compactor.merge.await_args.args[1]
    assert [turn.text for turn in turns] == [
        "turn 0",
        "turn 1",
        "turn 2",
        "turn 3",
    ]
    assert compactor.merge.await_args.kwargs == {}
    session.rollback.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test_compaction_skips_short_buffer():
    conversation_id = uuid4()
    user_id = uuid4()
    message_service = AsyncMock()
    conversation_service = AsyncMock()
    compactor = AsyncMock()
    service = ConversationMemoryService(
        session=AsyncMock(),
        conversation_service=conversation_service,
        message_service=message_service,
        settings=Settings(
            memory_compaction_max_messages=6,
            memory_compaction_max_tokens=100_000,
        ),
        compactor=compactor,
    )
    conversation_service.get_conversation.return_value = Conversation(
        id=conversation_id,
        user_id=user_id,
    )
    service._get_summary_state = AsyncMock(return_value=None)
    message_service.get_messages_after.return_value = [
        _message(conversation_id, MessageRole.user, "short")
    ]

    compacted = await service.compact_if_needed(
        conversation_id,
        user_id=user_id,
    )

    assert compacted is False
    compactor.merge.assert_not_awaited()


async def test_build_context_includes_selected_documents_catalog_when_memory_disabled():
    conversation = Conversation(id=uuid4(), user_id=uuid4())
    message_service = AsyncMock()
    message_service.get_messages_after.return_value = [
        _message(conversation.id, MessageRole.user, "What did the author say?")
    ]
    service = ConversationMemoryService(
        session=AsyncMock(),
        conversation_service=AsyncMock(),
        message_service=message_service,
        settings=Settings(memory_enabled=False),
        compactor=AsyncMock(),
    )
    service._get_summary_state = AsyncMock(
        return_value=ConversationSummary(
            conversation_id=conversation.id,
            documents_summary="A video about Go 1.27.",
        )
    )

    messages = await service.build_context_for_agent(
        conversation,
        documents_catalog=(
            "Selected this turn (searchable with search_documents)\n"
            "<<UNTRUSTED_DOCUMENT>>\n- dogs.pdf\n<</UNTRUSTED_DOCUMENT>>"
        ),
    )

    assert [type(message) for message in messages] == [SystemMessage, HumanMessage]
    assert "dogs.pdf" in messages[0].content
    assert "<<UNTRUSTED_DOCUMENT>>" in messages[0].content
    assert "A video about Go 1.27." not in messages[0].content
    assert "not evidence" in messages[0].content.lower()
    assert "not selected" in messages[0].content


async def test_build_context_omits_stored_documents_summary_without_turn_catalog():
    conversation = Conversation(id=uuid4(), user_id=uuid4())
    message_service = AsyncMock()
    message_service.get_messages_after.return_value = [
        _message(conversation.id, MessageRole.user, "Hello")
    ]
    service = ConversationMemoryService(
        session=AsyncMock(),
        conversation_service=AsyncMock(),
        message_service=message_service,
        settings=Settings(memory_enabled=False),
        compactor=AsyncMock(),
    )
    service._get_summary_state = AsyncMock(
        return_value=ConversationSummary(
            conversation_id=conversation.id,
            documents_summary="A video about Go 1.27.",
        )
    )

    messages = await service.build_context_for_agent(conversation)

    assert [type(message) for message in messages] == [HumanMessage]
    assert messages[0].content == "Hello"


async def test_upsert_documents_summary_writes_catalog_column():
    conversation_id = uuid4()
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(rowcount=1)
    service = ConversationMemoryService(
        session=session,
        conversation_service=AsyncMock(),
        message_service=AsyncMock(),
        settings=Settings(memory_enabled=False),
        compactor=AsyncMock(),
    )

    await service.upsert_documents_summary(conversation_id, "Catalog text")

    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()
