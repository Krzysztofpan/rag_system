from types import SimpleNamespace
from unittest.mock import patch

from app.agent.agent_orchestrator import build_system_prompt, get_agent_orchestrator
from app.tools.search_documents import search_documents
from app.tools.summarize_context import summarize_context
from app.tools.web_search import web_search_tavily


def test_system_prompt_keeps_document_runtime_context_out_of_prefix():
    prompt = build_system_prompt()

    assert "injected into tools automatically" in prompt
    assert "Never ask for document IDs" in prompt
    assert "call summarize_context immediately" in prompt


def test_system_prompt_treats_retrieved_text_as_untrusted():
    prompt = build_system_prompt()

    assert "<<UNTRUSTED_DOCUMENT>>" in prompt
    assert "not instructions" in prompt


def test_system_prompt_explains_missing_document_results():
    prompt = build_system_prompt()

    assert "no information was found" in prompt
    assert "select documents" in prompt


def test_system_prompt_forbids_answering_from_general_knowledge():
    prompt = build_system_prompt()

    assert "Never answer from your own knowledge" in prompt
    assert "call search_documents" in prompt
    assert "even if the answer seems obvious" in prompt


def test_system_prompt_is_stable():
    assert build_system_prompt() == build_system_prompt()


def test_summarize_context_schema_does_not_ask_llm_for_ids():
    schema = summarize_context.tool_call_schema.model_json_schema()
    properties = schema.get("properties", {})
    description = summarize_context.description.lower()

    assert "document_ids" not in properties
    assert "conversation_id" not in properties
    assert "user_id" not in properties
    assert "do not ask the user" in description


def test_search_documents_description_requires_lookup_before_answering():
    description = search_documents.description.lower()

    assert "do not skip" in description
    assert "general knowledge" in description
    assert "do not ask the user" in description


@patch("app.agent.agent_orchestrator.create_agent")
@patch("app.agent.agent_orchestrator.get_settings")
def test_orchestrator_graph_is_named_chat(get_settings, create_agent):
    get_settings.return_value = SimpleNamespace(orchestrator_model="gpt-4o")
    get_agent_orchestrator.cache_clear()
    try:
        get_agent_orchestrator()
    finally:
        get_agent_orchestrator.cache_clear()

    assert create_agent.call_args.kwargs["name"] == "chat"
    assert create_agent.call_args.kwargs["tools"] == [
        search_documents,
        summarize_context,
        web_search_tavily,
    ]
