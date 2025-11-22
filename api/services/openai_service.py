from functools import lru_cache
from typing import Any, Iterable, List, Mapping, Optional, Sequence

from openai import OpenAI

from core.config import settings


class OpenAIService:
    """Wrapper around the OpenAI SDK so other services stay decoupled."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        if not (api_key or settings.openai_api_key):
            raise RuntimeError(
                "OpenAI API key is not configured. "
                "Set OPENAI_API_KEY env var or provide api_key explicitly."
            )

        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.default_model = default_model or settings.openai_default_model
        self.embedding_model = embedding_model or settings.openai_embedding_model

    def chat_completion(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Create a chat completion with sensible defaults."""
        return self.client.chat.completions.create(
            model=model or self.default_model,
            messages=list(messages),
            **kwargs,
        )

    def create_embedding(
        self,
        *,
        input_texts: Iterable[str],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Generate embeddings for one or more strings."""
        return self.client.embeddings.create(
            model=model or self.embedding_model,
            input=list(input_texts),
            **kwargs,
        )


@lru_cache()
def get_openai_service() -> OpenAIService:
    """FastAPI dependency factory."""
    return OpenAIService()
