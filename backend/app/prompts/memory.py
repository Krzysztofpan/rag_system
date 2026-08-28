MEMORY_COMPACTION_SYSTEM_PROMPT = (
    "Maintain a compact, factual memory of a conversation. "
    "Merge the previous memory with the new turns. Preserve only "
    "goals, established conversational facts, user preferences, "
    "and unresolved questions. Ignore greetings and repetition. "
    "Do not invent facts. Facts originating from documents are "
    "conversation memory only and must not be treated as document "
    "evidence by the answering agent."
)


def conversation_memory_system_message(summary_json: str) -> str:
    return (
        "Conversation memory for interpreting references and user "
        "preferences. It is not evidence about document contents:\n"
        f"{summary_json}"
    )


def conversation_documents_catalog_message(wrapped_catalog: str) -> str:
    return (
        "Catalog of documents available for this conversation. "
        "Use it only to decide whether to call search_documents. "
        "It is not evidence; do not answer from it.\n"
        f"{wrapped_catalog}"
    )


def memory_compaction_human_message(previous_memory: str, transcript: str) -> str:
    return (
        f"Previous memory:\n{previous_memory}\n\n"
        f"New conversation turns:\n{transcript}"
    )
