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

    openai_api_key: str | None = None
    parser_llm_model: str = "gpt-4o-mini"
    parser_ocr_repair: bool = True
    parser_llm_repair: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    return Settings()