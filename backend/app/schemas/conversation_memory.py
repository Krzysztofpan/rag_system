from pydantic import BaseModel, Field


class ConversationMemorySummary(BaseModel):
    goals_and_topics: list[str] = Field(default_factory=list)
    established_facts: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


EMPTY_MEMORY_SUMMARY = ConversationMemorySummary()
