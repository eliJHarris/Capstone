from functools import lru_cache
from types import SimpleNamespace
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

    def chat_completion(self, *, messages, model=None, **kwargs):
        response = self.client.responses.create(
            model=model or self.default_model,
            input=messages,
            **kwargs,
        )
        return self._coerce_response(response)

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

    @staticmethod
    def _coerce_response(response: Any) -> Any:
        """
        Normalize OpenAI Responses API output to look like the legacy chat.completions
        shape our callers expect (choices[].message.content, finish_reason, usage).
        """
        if getattr(response, "choices", None):
            return response

        content_parts: List[str] = []
        finish_reason = None
        output_items = getattr(response, "output", None) or []
        if output_items:
            first = output_items[0]
            finish_reason = getattr(first, "finish_reason", None) or getattr(first, "status", None)
            for item in getattr(first, "content", None) or []:
                text = getattr(item, "text", None)
                if text:
                    content_parts.append(str(text))

        message = SimpleNamespace(content="\n".join(content_parts))
        choice = SimpleNamespace(message=message, finish_reason=finish_reason)
        return SimpleNamespace(
            choices=[choice],
            model=getattr(response, "model", None),
            usage=getattr(response, "usage", None),
            _response=response,
        )


@lru_cache()
def get_openai_service() -> OpenAIService:
    """FastAPI dependency factory."""
    return OpenAIService()
