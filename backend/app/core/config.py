from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Proposal Intelligence Platform"
    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"

    llm_provider: str = "gemini"
    llm_model: str = ""
    gemini_api_key: str = Field(default="", repr=False)

    embedding_provider: str = "sentence-transformers"
    embedding_model: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    normalize_embeddings: bool = True

    max_agent_steps: int = Field(default=12, ge=1, le=50)
    max_agent_retries: int = Field(default=2, ge=0, le=5)
    max_llm_calls_per_assessment: int = Field(default=20, ge=1, le=100)

    database_url: str = "sqlite:///./proposal_intelligence.db"
    upload_directory: str = "../data/uploads"
    index_directory: str = "../data/indexes"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""

    return Settings()
