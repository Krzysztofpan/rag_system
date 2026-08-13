from types import SimpleNamespace

from app.agent.agent_orchestrator import agent_system_prompt, build_system_prompt
from app.tools.summarize_context import summarize_context


def test_prompt_tells_model_selected_documents_are_already_attached():
    prompt = build_system_prompt(2)

    assert "already selected 2 document" in prompt
    assert "Never ask for document IDs" in prompt
    assert "call summarize_context immediately" in prompt


def test_prompt_tells_model_when_no_documents_are_selected():
    prompt = build_system_prompt(0)

    assert "No documents are currently selected" in prompt
    assert "select documents first" in prompt


def test_dynamic_prompt_reads_document_ids_from_runtime_context():
    document_ids = ["a", "b", "c"]
    request = SimpleNamespace(
        runtime=SimpleNamespace(context={"document_ids": document_ids})
    )

    prompt = agent_system_prompt(request)

    assert "already selected 3 document" in prompt


def test_summarize_context_schema_does_not_ask_llm_for_ids():
    schema = summarize_context.tool_call_schema.model_json_schema()
    properties = schema.get("properties", {})
    description = summarize_context.description.lower()

    assert "document_ids" not in properties
    assert "conversation_id" not in properties
    assert "user_id" not in properties
    assert "do not ask the user" in description
