from pathlib import Path

from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
from typing import Literal

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

load_dotenv(ENV_FILE, override=True, interpolate=True)


class Settings(BaseSettings):
    uvicorn_host: str = "0.0.0.0"
    backend_port: int = 8000
    uvicorn_reload: bool = True
    uvicorn_reload_delay: int = 0
    uvicorn_timeout_graceful_shutdown: int = 5
    app_env: Literal["development", "production"] = "development"
    database_url: str | None = None
    database_password: str | None = None
    supabase_url: str | None = None
    cors_allow_origins: str = "http://localhost:5173"

    openai_api_key: str | None = None
    pinecone_api_key: str | None = None
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    parser_llm_model: str = "gpt-4o-mini"
    parser_ocr_repair: bool = True
    parser_llm_repair: bool = True
    parser_image_pipeline: Literal["vlm", "standard"] = "vlm"
    parser_vlm_model: str = "gpt-4o-mini"
    parser_vlm_timeout: float = 90
    parser_vlm_url: str = "https://api.openai.com/v1/chat/completions"
    parser_image_suffixes: tuple[str, ...] = (".png", ".jpg", ".jpeg")

    orchestrator_model: str = "gpt-4o"
    memory_enabled: bool = True
    memory_summarization_model: str = "gpt-4o-mini"
    memory_compaction_max_messages: int = 12
    memory_compaction_max_tokens: int = 2500
    memory_keep_recent_messages: int = 4
    memory_summary_max_tokens: int = 600
    # Reject the whole document only when this fraction of chunks is unusable.
    parser_max_rejected_chunk_ratio: float = 0.25

    embedding_model: str = "text-embedding-3-small"
    embedding_model_max_tokens: int = 512
    pinecone_index: str = "rag-system"

    cohere_api_key: str | None = None
    cohere_rerank_model: str = "rerank-v4.0-fast"
    rerank_min_score: float = 0

    groq_api_key: str | None = None

    tavily_api_key: str | None = None

    prompt_guard_model: str = "meta-llama/llama-prompt-guard-2-86m"
    prompt_guard_url: str = "https://api.groq.com"
    prompt_guard_threshold: float = 0.5
    prompt_guard_enabled: bool = True
    prompt_guard_fail_open: bool = True
    prompt_guard_timeout_sec: float = 8.0
    # Groq context is 512 tokens; requests around 500+ return 400.
    prompt_guard_max_prompt_tokens: int = 400

    azure_content_safety_endpoint: str | None = None
    azure_content_safety_key: str | None = None
    prompt_shields_enabled: bool = True
    prompt_shields_fail_open: bool = True
    prompt_shields_timeout_sec: float = 8.0
    prompt_shields_api_version: str = "2024-09-01"
    prompt_shields_max_documents: int = 5
    prompt_shields_max_document_chars: int = 10_000
    prompt_shields_max_prompt_chars: int = 10_000

    # YouTube STT fallback when captions are missing (off: ToS gray area).
    youtube_stt_enabled: bool = False
    youtube_max_duration_sec: int = 2700
    youtube_stt_max_bytes: int = 24 * 1024 * 1024
    youtube_stt_chunk_sec: int = 9 * 60
    youtube_stt_chunk_overlap_sec: int = 15

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    return Settings()