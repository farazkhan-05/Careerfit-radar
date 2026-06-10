from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    google_search_api_key: str = Field(default="", alias="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: str = Field(default="", alias="GOOGLE_SEARCH_ENGINE_ID")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-2",
        alias="GEMINI_EMBEDDING_MODEL",
    )
    gemini_llm_model: str = Field(
        default="gemini-3.1-flash-lite",
        alias="GEMINI_LLM_MODEL",
    )
    google_cloud_project: str | None = Field(
        default=None,
        alias="GOOGLE_CLOUD_PROJECT",
    )
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
