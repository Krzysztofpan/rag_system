from functools import lru_cache

# Prompt Guard 2 86M is mDeBERTa, not a Llama tokenizer. The official
# meta-llama/Llama-Prompt-Guard-2-86M tokenizer is gated; the public
# backbone tokenizer matches Groq's prompt_tokens closely.
_PROMPT_GUARD_TOKENIZER = "microsoft/mdeberta-v3-base"


@lru_cache
def get_prompt_guard_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(_PROMPT_GUARD_TOKENIZER)
