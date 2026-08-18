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

    orchestrator_model: str = "gpt-4o"
    evaluate_model: str = "gpt-5"
    # Reject the whole document only when this fraction of chunks is unusable.
    parser_max_rejected_chunk_ratio: float = 0.25

    embedding_model: str = "text-embedding-3-small"
    embedding_model_max_tokens: int = 512
    pinecone_index: str = "rag-system"

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