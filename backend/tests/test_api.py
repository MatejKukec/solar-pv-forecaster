"""API-level tests using FastAPI's TestClient."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.api.deps import get_open_meteo_client
from backend.main import app


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ai_provider"] == "mock"


def test_health_reports_gemini_when_api_key_set(client: TestClient) -> None:
    from backend.config import settings

    original = settings.gemini_api_key
    settings.gemini_api_key = "fake-key"
    try:
        response = client.get("/health")
        assert response.json()["ai_provider"] == "gemini"
    finally:
        settings.gemini_api_key = original


def test_forecast_success(client: TestClient, sample_weather_raw: dict) -> None:
    mock_client = AsyncMock()
    mock_client.get_forecast.return_value = sample_weather_raw
    app.dependency_overrides[get_open_meteo_client] = lambda: mock_client

    try:
        response = client.post(
            "/api/forecast",
            json={
                "location": {"latitude": 45.815, "longitude": 15.9819},
                "arrays": [{"capacity_kw": 5.0, "tilt_deg": 30, "azimuth_deg": 180}],
                "horizon_hours": 24,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["hourly"]) == 24
    assert body["total_capacity_kw"] == 5.0


def test_forecast_rejects_empty_arrays(client: TestClient) -> None:
    response = client.post(
        "/api/forecast",
        json={"location": {"latitude": 45.8, "longitude": 16.0}, "arrays": [], "horizon_hours": 24},
    )
    assert response.status_code == 422


def test_forecast_rejects_too_many_arrays(client: TestClient) -> None:
    arrays = [{"capacity_kw": 1.0, "tilt_deg": 30, "azimuth_deg": 180}] * 6
    response = client.post(
        "/api/forecast",
        json={"location": {"latitude": 45.8, "longitude": 16.0}, "arrays": arrays, "horizon_hours": 24},
    )
    assert response.status_code == 422


def test_ai_summary(client: TestClient) -> None:
    response = client.post("/api/ai/summary", json={"forecast_context": "sunny, 5kW system"})
    assert response.status_code == 200
    assert "summary" in response.json()


def test_ai_chat(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={"message": "How much will I generate today?"})
    assert response.status_code == 200
    assert "reply" in response.json()
