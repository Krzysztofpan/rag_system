from unittest.mock import patch
from uuid import uuid4

from app.lib.tracing import conversation_metadata, conversation_tracing


def test_conversation_metadata_uses_conversation_as_thread_id():
    conversation_id = uuid4()
    user_id = uuid4()
    document_id = uuid4()

    metadata = conversation_metadata(
        conversation_id,
        user_id=user_id,
        extra={"document_id": document_id},
    )
    assert metadata["thread_id"] == str(conversation_id)
    assert metadata["conversation_id"] == str(conversation_id)
    assert metadata["user_id"] == str(user_id)
    assert metadata["document_id"] == str(document_id)


@patch("app.lib.tracing.tracing_context")
def test_conversation_tracing_as_root_detaches_from_parent(tracing_context):
    conversation_id = uuid4()
    tracing_context.return_value.__enter__.return_value = None

    with conversation_tracing(conversation_id, tags=["retrieval"], as_root=True):
        pass

    assert tracing_context.call_args.kwargs["parent"] is False
    assert tracing_context.call_args.kwargs["tags"] == ["retrieval"]
    assert tracing_context.call_args.kwargs["metadata"]["thread_id"] == str(
        conversation_id
    )


@patch("app.lib.tracing.tracing_context")
def test_conversation_tracing_default_keeps_parent(tracing_context):
    conversation_id = uuid4()
    tracing_context.return_value.__enter__.return_value = None

    with conversation_tracing(conversation_id, tags=["chat"]):
        pass

    assert tracing_context.call_args.kwargs["parent"] is None
