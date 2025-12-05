from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized application configuration."""

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_default_model: str = Field(default="gpt-5.1")
    openai_embedding_model: str = Field(default="text-embedding-3-large")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
