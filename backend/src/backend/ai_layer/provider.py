"""AIProvider interface — swapping the AI backend touches one new class, nothing else."""

from typing import Protocol


class AIProvider(Protocol):
    """Structural interface every AI backend (mock, Gemini, Claude, ...) must implement."""

    async def summarize(self, forecast_context: str) -> str:
        """Produce a plain-language summary of a forecast/production window."""
        ...

    async def chat(self, message: str, forecast_context: str) -> str:
        """Answer a conversational question, grounded in the given forecast context."""
        ...

    async def flag_anomaly(self, actual_kw: float, expected_kw: float, context: str) -> str | None:
        """Return a plain-language anomaly explanation, or None if nothing is anomalous."""
        ...
