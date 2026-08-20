from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import BackgroundTasks
from langchain_core.messages import AIMessage, HumanMessage

from app.app import chat
from app.auth.deps import AuthenticatedUser
from app.db.models.conversation import Conversation
from app.schemas.chat import ChatRequestBody


async def test_chat_passes_memory_once_persists_messages_and_schedules_compaction():
    user_id = uuid4()
    conversation_id = uuid4()
    current_user = AuthenticatedUser(
        access_token="token",
        user_id=user_id,
        email=None,
        role="authenticated",
        phone=None,
        app_metadata={},
        user_metadata={},
    )
    conversation = Conversation(id=conversation_id, user_id=user_id)
    conversation_service = AsyncMock()
    conversation_service.get_conversation.return_value = conversation
    message_service = AsyncMock()
    message_service.create_message.side_effect = lambda message: message
    memory_service = AsyncMock()

    async def build_context(passed_conversation):
        assert passed_conversation is conversation
        assert message_service.create_message.await_count == 1
        return [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
            HumanMessage(content="Current question"),
        ]

    memory_service.build_context_for_agent.side_effect = build_context
    agent = AsyncMock()
    agent.ainvoke.return_value = {
        "messages": [AIMessage(content="Current answer")]
    }
    background_tasks = BackgroundTasks()
    body = ChatRequestBody(
        conversation_id=conversation_id,
        message="Current question",
        document_ids=[],
    )

    with patch("app.app.get_agent_orchestrator", return_value=agent):
        response = await chat(
            current_user=current_user,
            conversation_service=conversation_service,
            message_service=message_service,
            memory_service=memory_service,
            background_tasks=background_tasks,
            body=body,
        )

    invoke_messages = agent.ainvoke.await_args.args[0]["messages"]
    assert sum(
        message.content == "Current question" for message in invoke_messages
    ) == 1
    assert message_service.create_message.await_count == 2
    assert response["response"].text == "Current answer"
    assert len(background_tasks.tasks) == 1
