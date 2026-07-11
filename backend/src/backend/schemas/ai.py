"""Request/response schemas for the AI chat and summary endpoints."""

from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    """Request body for a plain-language forecast summary."""

    forecast_context: str = Field(min_length=1, max_length=4000)


class SummaryResponse(BaseModel):
    """A plain-language forecast summary."""

    summary: str


class ChatRequest(BaseModel):
    """Request body for a conversational Q&A turn."""

    message: str = Field(min_length=1, max_length=1000)
    forecast_context: str = Field(default="", max_length=4000)


class ChatResponse(BaseModel):
    """A conversational AI reply."""

    reply: str


class AnomalyRequest(BaseModel):
    """Request body for anomaly flagging: actual vs. expected output."""

    actual_kw: float = Field(ge=0)
    expected_kw: float = Field(ge=0)
    context: str = Field(default="", max_length=2000)


class AnomalyResponse(BaseModel):
    """Plain-language anomaly explanation, or null if nothing is anomalous."""

    message: str | None
