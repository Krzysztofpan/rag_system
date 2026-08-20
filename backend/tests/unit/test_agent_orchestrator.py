from app.agent.agent_orchestrator import build_system_prompt
from app.tools.summarize_context import summarize_context


def test_system_prompt_keeps_document_runtime_context_out_of_prefix():
    prompt = build_system_prompt()

    assert "injected into tools automatically" in prompt
    assert "Never ask for document IDs" in prompt
    assert "call summarize_context immediately" in prompt


def test_system_prompt_explains_missing_document_results():
    prompt = build_system_prompt()

    assert "no information was found" in prompt
    assert "select documents" in prompt


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
