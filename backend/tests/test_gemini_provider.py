"""Tests for backend.ai_layer.gemini_provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.ai_layer.exceptions import AIProviderError
from backend.ai_layer.gemini_provider import GeminiProvider


def _mock_response(json_body: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError("error", request=MagicMock(), response=response)
    else:
        response.raise_for_status.return_value = None
    return response


def _text_response(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_missing_api_key_raises() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiProvider(api_key="")


@pytest.mark.asyncio
async def test_summarize_returns_gemini_text() -> None:
    provider = GeminiProvider(api_key="fake-key", model="gemini-flash")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response(_text_response("Sunny today.")))):
        result = await provider.summarize("5kW system, clear skies")
    assert result == "Sunny today."


@pytest.mark.asyncio
async def test_chat_includes_context_and_question() -> None:
    provider = GeminiProvider(api_key="fake-key")
    mock_post = AsyncMock(return_value=_mock_response(_text_response("About 20 kWh.")))
    with patch("httpx.AsyncClient.post", new=mock_post):
        result = await provider.chat("How much today?", "5kW system, clear skies")
    assert result == "About 20 kWh."
    sent_body = mock_post.call_args.kwargs["json"]
    assert "How much today?" in sent_body["contents"][0]["parts"][0]["text"]
    assert "clear skies" in sent_body["contents"][0]["parts"][0]["text"]


@pytest.mark.asyncio
async def test_flag_anomaly_below_threshold_skips_api_call() -> None:
    provider = GeminiProvider(api_key="fake-key")
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        result = await provider.flag_anomaly(actual_kw=4.8, expected_kw=5.0, context="")
    assert result is None
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_flag_anomaly_above_threshold_calls_api() -> None:
    provider = GeminiProvider(api_key="fake-key")
    body = _text_response("Likely cloud cover.")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response(body))):
        result = await provider.flag_anomaly(actual_kw=2.0, expected_kw=5.0, context="clear forecast")
    assert result == "Likely cloud cover."


@pytest.mark.asyncio
async def test_flag_anomaly_zero_expected_returns_none() -> None:
    provider = GeminiProvider(api_key="fake-key")
    result = await provider.flag_anomaly(actual_kw=1.0, expected_kw=0.0, context="")
    assert result is None


@pytest.mark.asyncio
async def test_malformed_response_raises_ai_provider_error() -> None:
    provider = GeminiProvider(api_key="fake-key")
    with (
        patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response({"candidates": []}))),
        pytest.raises(AIProviderError, match="missing expected text content"),
    ):
        await provider.summarize("context")


@pytest.mark.asyncio
async def test_non_retryable_status_fails_on_first_attempt() -> None:
    """A 404 (e.g. a bad model name) shouldn't be retried — it won't fix itself."""
    provider = GeminiProvider(api_key="fake-key")
    mock_post = AsyncMock(return_value=_mock_response({}, status_code=404))
    with patch("httpx.AsyncClient.post", new=mock_post), pytest.raises(AIProviderError, match="HTTP 404"):
        await provider.summarize("context")
    assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_retryable_status_retries_then_raises_cleanly() -> None:
    """A 503 (transient overload) should be retried, and still wrapped cleanly if it never recovers."""
    provider = GeminiProvider(api_key="fake-key")
    mock_post = AsyncMock(return_value=_mock_response({}, status_code=503))
    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("asyncio.sleep", new=AsyncMock()),  # skip real backoff delays
        pytest.raises(AIProviderError, match="HTTP 503"),
    ):
        await provider.summarize("context")
    assert mock_post.call_count == 3  # stop_after_attempt(3)


@pytest.mark.asyncio
async def test_retryable_status_recovers_on_later_attempt() -> None:
    provider = GeminiProvider(api_key="fake-key")
    mock_post = AsyncMock(
        side_effect=[_mock_response({}, status_code=503), _mock_response(_text_response("Recovered."))]
    )
    with patch("httpx.AsyncClient.post", new=mock_post), patch("asyncio.sleep", new=AsyncMock()):
        result = await provider.summarize("context")
    assert result == "Recovered."
    assert mock_post.call_count == 2


def test_is_retryable_predicate() -> None:
    from backend.ai_layer.gemini_provider import _is_retryable

    def _status_error(status_code: int) -> httpx.HTTPStatusError:
        response = MagicMock(status_code=status_code)
        return httpx.HTTPStatusError("error", request=MagicMock(), response=response)

    assert _is_retryable(_status_error(429)) is True
    assert _is_retryable(_status_error(503)) is True
    assert _is_retryable(_status_error(404)) is False
    assert _is_retryable(_status_error(400)) is False
    assert _is_retryable(httpx.ConnectError("boom")) is True
    assert _is_retryable(ValueError("unrelated")) is False
