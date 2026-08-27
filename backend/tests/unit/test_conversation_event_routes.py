import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.auth.deps import AuthenticatedUser
from app.db.models.conversation import Conversation
from app.routes.conversation_routes import conversation_events
from app.services.conversation_events import HEARTBEAT, conversation_title_event


def _current_user(user_id):
    return AuthenticatedUser(
        access_token="token",
        user_id=user_id,
        email=None,
        role="authenticated",
        phone=None,
        app_metadata={},
        user_metadata={},
    )


async def test_conversation_events_streams_title_and_heartbeat():
    user_id = uuid4()
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Contracts and invoices")
    conversation_service = AsyncMock()
    conversation_service.get_conversation.return_value = Conversation(
        id=conversation_id,
        user_id=user_id,
    )

    class Subscription:
        async def events(self):
            yield event
            yield HEARTBEAT

    broker = AsyncMock()
    broker.subscribe.return_value = Subscription()
    request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))

    response = await conversation_events(
        conversation_id=conversation_id,
        request=request,
        current_user=_current_user(user_id),
        conversation_service=conversation_service,
        broker=broker,
    )

    first_chunk = await anext(response.body_iterator)
    second_chunk = await anext(response.body_iterator)
    await response.body_iterator.aclose()

    assert json.loads(first_chunk.removeprefix("data: ").strip()) == event
    assert second_chunk == ": heartbeat\n\n"
    broker.subscribe.assert_awaited_once_with(conversation_id)
    conversation_service.get_conversation.assert_awaited_once_with(
        conversation_id,
        user_id=user_id,
    )
