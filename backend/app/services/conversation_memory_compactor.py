from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings
from app.db.models.message import MessageRole
from app.schemas.conversation_memory import ConversationMemorySummary


@dataclass(frozen=True)
class MemoryTurn:
    role: MessageRole
    text: str


class ConversationMemoryCompactor:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = ChatOpenAI(
            model=self.settings.memory_summarization_model,
            temperature=0,
            max_tokens=self.settings.memory_summary_max_tokens,
        ).with_structured_output(ConversationMemorySummary)

    async def merge(
        self,
        existing_summary: ConversationMemorySummary | None,
        turns: list[MemoryTurn],
    ) -> ConversationMemorySummary:
        current = (
            existing_summary.model_dump_json()
            if existing_summary is not None
            else "{}"
        )
        transcript = "\n".join(
            f"{turn.role.value}: {turn.text}" for turn in turns
        )
        response = await self.model.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Maintain a compact, factual memory of a conversation. "
                        "Merge the previous memory with the new turns. Preserve only "
                        "goals, established conversational facts, user preferences, "
                        "and unresolved questions. Ignore greetings and repetition. "
                        "Do not invent facts. Facts originating from documents are "
                        "conversation memory only and must not be treated as document "
                        "evidence by the answering agent."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Previous memory:\n{current}\n\n"
                        f"New conversation turns:\n{transcript}"
                    )
                ),
            ]
        )
        if not isinstance(response, ConversationMemorySummary):
            return ConversationMemorySummary.model_validate(response)
        return response
