"""Gemini-backed AIProvider — the real backend, swapped in for MockProvider on Day 3.

Talks to the Gemini REST API directly (`generateContent`) rather than pulling
in the SDK — consistent with the httpx-based clients elsewhere in
data_ingestion, and this only needs three simple text-generation calls.

Free-tier data privacy note (Section 3 of the dev plan): Google may use
free-tier prompts/responses to improve their models. Don't pass anything
here you wouldn't want retained.
"""

from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from backend.ai_layer.exceptions import AIProviderError
from backend.config import settings

_TRANSIENT = (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)
_RETRYABLE_STATUS_CODES = {429, 503}
_TIMEOUT = httpx.Timeout(15.0, connect=5.0, read=25.0)
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _is_retryable(exc: BaseException) -> bool:
    """Retry connection-level failures, plus 429 (rate limited) and 503 (overloaded) —
    but not 4xx errors like a bad model name or invalid key, which won't fix themselves."""
    if isinstance(exc, _TRANSIENT):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in _RETRYABLE_STATUS_CODES


_SUMMARY_SYSTEM_PROMPT = (
    "You are a solar PV assistant. Summarize the forecast/production context in 2-3 plain-language "
    "sentences a homeowner would understand. No jargon, no markdown, no bullet points."
)
_CHAT_SYSTEM_PROMPT = (
    "You are a solar PV assistant for a specific site. Two kinds of questions: "
    "(1) Questions about this site's own data (its forecast, production, calibration) — answer only "
    "from the given context, and say so plainly if the context doesn't cover it. Never guess a number. "
    "(2) General solar PV knowledge questions not about this specific site (e.g. how panels work, why "
    "temperature affects output) — answer from your own knowledge; the context doesn't need to cover these. "
    "Keep answers under 3 sentences."
)
_ANOMALY_SYSTEM_PROMPT = (
    "You are a solar PV assistant. Given an actual vs. expected output deviation, explain in one "
    "plain-language sentence what might cause it (e.g. cloud cover, soiling, shading, an inverter fault). "
    "Be tentative, not certain — you don't have direct sensor access."
)


class GeminiProvider:
    """AIProvider backed by the Gemini API (Flash / Flash-Lite, free tier)."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model if model is not None else settings.gemini_model
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not set")

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> httpx.Response:
        url = f"{_BASE_URL}/models/{self._model}:generateContent"
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, params={"key": self._api_key}, json=body)
            response.raise_for_status()
            return response

    async def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini's generateContent endpoint and extract the text reply.

        Raises:
            AIProviderError: If the request fails (bad model/key, rate limited
                after retries, Gemini unreachable, or a malformed response).
        """
        try:
            response = await self._call_gemini(system_prompt, user_prompt)
        except httpx.HTTPStatusError as e:
            raise AIProviderError("gemini", f"HTTP {e.response.status_code} from Gemini") from e
        except httpx.HTTPError as e:
            raise AIProviderError("gemini", f"request failed: {e}") from e

        try:
            data = response.json()
            return str(data["candidates"][0]["content"]["parts"][0]["text"]).strip()
        except (KeyError, IndexError, ValueError) as e:
            raise AIProviderError("gemini", "response missing expected text content") from e

    async def summarize(self, forecast_context: str) -> str:
        """Return a Gemini-generated plain-language summary."""
        return await self._generate(_SUMMARY_SYSTEM_PROMPT, forecast_context)

    async def chat(self, message: str, forecast_context: str) -> str:
        """Return a Gemini-generated reply, grounded in the given forecast context."""
        prompt = f"Context:\n{forecast_context}\n\nQuestion: {message}"
        return await self._generate(_CHAT_SYSTEM_PROMPT, prompt)

    async def flag_anomaly(self, actual_kw: float, expected_kw: float, context: str) -> str | None:
        """Return a Gemini-generated anomaly explanation, or None below the 20% deviation threshold."""
        if expected_kw <= 0:
            return None
        deviation_pct = abs(actual_kw - expected_kw) / expected_kw * 100
        if deviation_pct < 20:
            return None
        prompt = (
            f"Actual output: {actual_kw:.2f} kW. Expected: {expected_kw:.2f} kW "
            f"({deviation_pct:.0f}% deviation). Context: {context}"
        )
        return await self._generate(_ANOMALY_SYSTEM_PROMPT, prompt)
