"""API-level tests for the Day 3 AI additions: anomaly endpoint, provider selection."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.ai_layer import AIProviderError, GeminiProvider, MockProvider
from backend.api.deps import get_ai_provider
from backend.config import settings
from backend.main import app


def test_ai_anomaly_flags_deviation(client: TestClient) -> None:
    response = client.post("/api/ai/anomaly", json={"actual_kw": 2.0, "expected_kw": 5.0, "context": ""})
    assert response.status_code == 200
    assert response.json()["message"] is not None


def test_ai_anomaly_no_deviation_returns_null(client: TestClient) -> None:
    response = client.post("/api/ai/anomaly", json={"actual_kw": 4.9, "expected_kw": 5.0, "context": ""})
    assert response.status_code == 200
    assert response.json()["message"] is None


def test_ai_provider_failure_returns_clean_502(client: TestClient) -> None:
    """An AIProviderError (bad model name, Gemini down, etc.) should surface as a
    502 with a real, readable message — not an unhandled 500 with a raw traceback,
    and not FastAPI's default {"detail": ...} shape, which the frontend doesn't parse."""
    failing_provider = AsyncMock()
    failing_provider.chat.side_effect = AIProviderError("gemini", "HTTP 503 from Gemini")
    app.dependency_overrides[get_ai_provider] = lambda: failing_provider

    try:
        response = client.post("/api/ai/chat", json={"message": "hi", "forecast_context": ""})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    body = response.json()
    assert "gemini" in body["error"]["message"]
    assert "503" in body["error"]["message"]


def test_ai_summary_failure_returns_clean_502(client: TestClient) -> None:
    failing_provider = AsyncMock()
    failing_provider.summarize.side_effect = AIProviderError("gemini", "HTTP 404 from Gemini")
    app.dependency_overrides[get_ai_provider] = lambda: failing_provider

    try:
        response = client.post("/api/ai/summary", json={"forecast_context": "5kW system"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "404" in response.json()["error"]["message"]


def test_ai_anomaly_failure_returns_clean_502(client: TestClient) -> None:
    failing_provider = AsyncMock()
    failing_provider.flag_anomaly.side_effect = AIProviderError("gemini", "HTTP 503 from Gemini")
    app.dependency_overrides[get_ai_provider] = lambda: failing_provider

    try:
        response = client.post("/api/ai/anomaly", json={"actual_kw": 2.0, "expected_kw": 5.0, "context": ""})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "503" in response.json()["error"]["message"]


def test_get_ai_provider_defaults_to_mock_without_api_key() -> None:
    original = settings.gemini_api_key
    settings.gemini_api_key = ""
    try:
        assert isinstance(get_ai_provider(), MockProvider)
    finally:
        settings.gemini_api_key = original


def test_get_ai_provider_uses_gemini_with_api_key() -> None:
    original = settings.gemini_api_key
    settings.gemini_api_key = "fake-key"
    try:
        assert isinstance(get_ai_provider(), GeminiProvider)
    finally:
        settings.gemini_api_key = original
