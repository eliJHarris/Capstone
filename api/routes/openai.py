from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
)
from services.openai_service import OpenAIService, get_openai_service

router = APIRouter(
    prefix="/openai",
    tags=["openai"],
)


def _build_messages(payload: ChatCompletionRequest) -> list[dict[str, str]]:
    """Translate the prompt payload into the OpenAI chat format."""
    return [{"role": "user", "content": payload.prompt}]


@router.post("/chat", response_model=ChatCompletionResponse)
async def create_chat_completion(
    payload: ChatCompletionRequest,
) -> ChatCompletionResponse:
    try:
        openai_service: OpenAIService = get_openai_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        completion = await run_in_threadpool(
            openai_service.chat_completion,
            messages=_build_messages(payload),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"OpenAI API call failed: {exc}"
        ) from exc

    try:
        choice = completion.choices[0]
        content = choice.message.content
        finish_reason = getattr(choice, "finish_reason", None)
    except (AttributeError, IndexError, KeyError) as exc:
        raise HTTPException(
            status_code=500, detail="OpenAI response did not include a completion."
        ) from exc

    usage = getattr(completion, "usage", None)
    usage_payload = (
        ChatCompletionUsage(
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
        if usage
        else None
    )

    return ChatCompletionResponse(
        content=content,
        model=getattr(completion, "model", None) or openai_service.default_model,
        finish_reason=finish_reason,
        usage=usage_payload,
    )
