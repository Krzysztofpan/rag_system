import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.db.models import Message
from app.dependencies import (
    ConversationMemoryServiceDep,
    ConversationServiceDep,
    CurrentUserDep,
    MessageServiceDep,
    PromptGuardServiceDep,
    RunRegistryDep,
)
from app.schemas.chat import (
    ChatRunInput,
    ProtocolCommand,
    StreamSubscriptionRequest,
)
from app.services.chat.run_session import HEARTBEAT, RunSession
from app.services.chat.stream_runner import ChatStreamRunner
from app.services.security import PROMPT_ATTACK_MESSAGE

chat_stream_router = APIRouter(
    prefix="/conversations",
    tags=["chat-stream"],
)


def _command_error(
    command_id: int,
    message: str,
    *,
    code: str = "invalid_argument",
) -> dict[str, Any]:
    return {
        "type": "error",
        "id": command_id,
        "error": code,
        "message": message,
    }


@chat_stream_router.post("/{conversation_id}/commands")
async def chat_commands(
    conversation_id: UUID,
    command: ProtocolCommand,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    message_service: MessageServiceDep,
    memory_service: ConversationMemoryServiceDep,
    registry: RunRegistryDep,
    prompt_guard: PromptGuardServiceDep,
) -> dict[str, Any]:
    if command.method != "run.start":
        return _command_error(
            command.id,
            f"Unsupported command: {command.method}",
            code="unknown_command",
        )

    raw_input = command.params.get("input")
    try:
        run_input = ChatRunInput.model_validate(raw_input)
    except ValidationError as exc:
        return _command_error(command.id, str(exc))
    if not run_input.messages:
        return _command_error(command.id, "At least one human message is required")

    latest_message = run_input.messages[-1]
    try:
        conversation = await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if await prompt_guard.should_block_message(
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        text=latest_message.content,
    ):
        return _command_error(
            command.id,
            PROMPT_ATTACK_MESSAGE,
            code="prompt_attack",
        )

    run_id = str(uuid4())
    prepared: asyncio.Future[list] = asyncio.get_running_loop().create_future()

    async def execute(session: RunSession) -> None:
        conversation_context = await prepared
        runner = ChatStreamRunner(
            session,
            conversation_id=conversation_id,
            user_id=current_user.user_id,
            document_ids=run_input.document_ids,
            conversation_context=conversation_context,
            user_query=latest_message.content,
        )
        await runner.run()

    try:
        run_session = await registry.start(conversation_id, run_id, execute)
    except RuntimeError as exc:
        return _command_error(
            command.id,
            str(exc),
            code="invalid_argument",
        )

    try:
        await message_service.create_message(
            Message(
                id=latest_message.id,
                conversation_id=conversation_id,
                text=latest_message.content,
                role="user",
            )
        )
        conversation_context = await memory_service.build_context_for_agent(
            conversation,
        )
        prepared.set_result(conversation_context)
    except BaseException:
        if not prepared.done():
            prepared.cancel()
        if run_session.task is not None:
            run_session.task.cancel()
        await registry.remove_if_current(conversation_id, run_session)
        raise

    return {
        "type": "success",
        "id": command.id,
        "result": {"run_id": run_id},
    }


@chat_stream_router.post("/{conversation_id}/stream")
async def chat_stream(
    conversation_id: UUID,
    request: StreamSubscriptionRequest,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
    registry: RunRegistryDep,
) -> StreamingResponse:
    try:
        await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session = await registry.get(conversation_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No run for this conversation")

    subscription = await session.subscribe(
        channels=set(request.channels),
        namespaces=request.namespaces,
        depth=request.depth,
        since=request.since,
    )

    async def generate():
        current_session = session
        current_subscription = subscription
        while True:
            async for event in current_subscription.events():
                if event is HEARTBEAT:
                    yield ": heartbeat\n\n"
                else:
                    yield (
                        f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
                    )

            next_session = None
            while next_session is None:
                next_session = await registry.wait_for_session_after(
                    conversation_id,
                    current_session,
                    timeout=5,
                )
                if next_session is None:
                    yield ": heartbeat\n\n"

            current_session = next_session
            current_subscription = await current_session.subscribe(
                channels=set(request.channels),
                namespaces=request.namespaces,
                depth=request.depth,
                since=None,
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_stream_router.get("/{conversation_id}/state")
async def chat_state(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    conversation_service: ConversationServiceDep,
) -> dict[str, Any]:
    try:
        await conversation_service.get_conversation(
            conversation_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "values": {"messages": []},
        "next": [],
        "tasks": [],
    }
