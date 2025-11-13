from typing import Optional

from pydantic import BaseModel, Field


class ChatCompletionRequest(BaseModel):
    """Only accept the user prompt; everything else is fixed server-side."""

    prompt: str = Field(..., min_length=1)


class ChatCompletionUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class ChatCompletionResponse(BaseModel):
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[ChatCompletionUsage] = None
