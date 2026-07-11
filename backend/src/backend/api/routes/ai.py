"""AI routes: plain-language summaries, conversational Q&A, anomaly flagging."""

import structlog
from fastapi import APIRouter, HTTPException

from backend.ai_layer import AIProviderError
from backend.api.deps import AIProviderDep
from backend.schemas import (
    AnomalyRequest,
    AnomalyResponse,
    ChatRequest,
    ChatResponse,
    SummaryRequest,
    SummaryResponse,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = structlog.get_logger()


@router.post("/summary")
async def summarize(request: SummaryRequest, provider: AIProviderDep) -> SummaryResponse:
    """Return a plain-language summary of the given forecast context.

    Raises:
        HTTPException: 502 if the AI provider fails.
    """
    try:
        summary = await provider.summarize(request.forecast_context)
    except AIProviderError as e:
        logger.warning("ai_provider_failed", provider=e.provider, error=str(e))
        raise HTTPException(status_code=502, detail=f"AI provider unavailable: {e}") from e
    return SummaryResponse(summary=summary)


@router.post("/chat")
async def chat(request: ChatRequest, provider: AIProviderDep) -> ChatResponse:
    """Answer a conversational question, grounded in the given forecast context.

    Raises:
        HTTPException: 502 if the AI provider fails.
    """
    try:
        reply = await provider.chat(request.message, request.forecast_context)
    except AIProviderError as e:
        logger.warning("ai_provider_failed", provider=e.provider, error=str(e))
        raise HTTPException(status_code=502, detail=f"AI provider unavailable: {e}") from e
    return ChatResponse(reply=reply)


@router.post("/anomaly")
async def flag_anomaly(request: AnomalyRequest, provider: AIProviderDep) -> AnomalyResponse:
    """Flag a plain-language explanation if actual output deviates meaningfully from expected.

    Raises:
        HTTPException: 502 if the AI provider fails.
    """
    try:
        message = await provider.flag_anomaly(request.actual_kw, request.expected_kw, request.context)
    except AIProviderError as e:
        logger.warning("ai_provider_failed", provider=e.provider, error=str(e))
        raise HTTPException(status_code=502, detail=f"AI provider unavailable: {e}") from e
    return AnomalyResponse(message=message)
