from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized application configuration."""

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_default_model: str = Field(default="gpt-5.1")
    openai_embedding_model: str = Field(default="text-embedding-3-large")

    # SMTP Config
    smtp_host: str = Field(..., alias="SMTP_HOST")
    smtp_port: int = Field(..., alias="SMTP_PORT")
    smtp_user: str = Field(..., alias="SMTP_USER")
    smtp_password: str = Field(..., alias="SMTP_PASSWORD")
    smtp_from: str = Field(..., alias="SMTP_FROM")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "forbid"  # keep strict validation


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
