from typing import List, Optional

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    sender: str = Field(..., description="Sender label, e.g. user or assistant")
    text: str = Field(..., min_length=1)


class ChatCompletionRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    advisee_id: Optional[int] = Field(default=None, description="Advisee ID to load context for")
    schedule_id: Optional[int] = Field(default=None, description="Schedule ID to load context for")
    history: List[ChatHistoryItem] = Field(default_factory=list)
    requester_role: Optional[str] = Field(default=None, description="Who is asking (student/advisor/admin)")


class ChatCompletionUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class ChatCompletionResponse(BaseModel):
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[ChatCompletionUsage] = None
