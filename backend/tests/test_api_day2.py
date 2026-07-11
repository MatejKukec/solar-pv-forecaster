"""API-level tests for the Day 2 routes: calibration, past, analytics."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.api.deps import get_open_meteo_client, get_pvgis_client
from backend.main import app

_LOCATION = {"latitude": 45.815, "longitude": 15.9819}
_ARRAY = {"capacity_kw": 5.0, "tilt_deg": 30, "azimuth_deg": 180}


def test_log_production_and_status(client: TestClient) -> None:
    response = client.post(
        "/api/calibration/production", json={"location": _LOCATION, "date": "2026-06-01", "actual_kwh": 20.0}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["n_days_logged"] == 1
    assert body["is_calibrated"] is False

    status = client.get("/api/calibration/status", params=_LOCATION)
    assert status.status_code == 200
    assert status.json()["site_id"] == body["site_id"]


def test_calibration_history_lists_logged_days_most_recent_first(client: TestClient) -> None:
    client.post("/api/calibration/production", json={"location": _LOCATION, "date": "2026-06-01", "actual_kwh": 10.0})
    client.post("/api/calibration/production", json={"location": _LOCATION, "date": "2026-06-03", "actual_kwh": 12.0})
    client.post("/api/calibration/production", json={"location": _LOCATION, "date": "2026-06-02", "actual_kwh": 11.0})

    response = client.get("/api/calibration/history", params=_LOCATION)
    assert response.status_code == 200
    body = response.json()
    assert body["n_days_logged"] == 3
    assert [e["date"] for e in body["entries"]] == ["2026-06-03", "2026-06-02", "2026-06-01"]


def test_calibration_history_empty_site(client: TestClient) -> None:
    response = client.get("/api/calibration/history", params={"latitude": 1.23, "longitude": 4.56})
    assert response.status_code == 200
    body = response.json()
    assert body["entries"] == []
    assert body["n_days_logged"] == 0
    assert body["is_calibrated"] is False


def test_log_production_rejects_bad_date(client: TestClient) -> None:
    response = client.post(
        "/api/calibration/production", json={"location": _LOCATION, "date": "06/01/2026", "actual_kwh": 20.0}
    )
    assert response.status_code == 422


def test_past_date_success(client: TestClient, sample_weather_raw: dict) -> None:
    mock_client = AsyncMock()
    mock_client.get_historical.return_value = sample_weather_raw
    app.dependency_overrides[get_open_meteo_client] = lambda: mock_client

    try:
        response = client.post("/api/past", json={"location": _LOCATION, "arrays": [_ARRAY], "date": "2026-07-09"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["modeled_kwh"] >= 0
    assert body["bias_factor"] == 1.0
    assert body["is_calibrated"] is False
    assert body["actual_kwh"] is None


def test_past_date_weather_failure_returns_502(client: TestClient) -> None:
    from backend.data_ingestion import DataSourceError

    mock_client = AsyncMock()
    mock_client.get_historical.side_effect = DataSourceError("open-meteo", "boom")
    app.dependency_overrides[get_open_meteo_client] = lambda: mock_client

    try:
        response = client.post("/api/past", json={"location": _LOCATION, "arrays": [_ARRAY], "date": "2026-07-09"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "open-meteo" in response.json()["error"]["message"]


def test_analytics_tilt_daily_mode(client: TestClient) -> None:
    response = client.post(
        "/api/analytics/tilt", json={"location": _LOCATION, "mode": "daily", "target_date": "2026-06-21"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "clearsky-simulation"
    assert 0 <= body["tilt_deg"] <= 90


def test_analytics_tilt_annual_uses_pvgis(client: TestClient) -> None:
    mock_pvgis = AsyncMock()
    mock_pvgis.get_optimal_angles.return_value = {
        "inputs": {"mounting_system": {"fixed": {"slope": {"value": 32}, "azimuth": {"value": 0}}}},
        "outputs": {"totals": {"fixed": {"E_y": 1500.0}}},
    }
    app.dependency_overrides[get_pvgis_client] = lambda: mock_pvgis

    try:
        response = client.post("/api/analytics/tilt", json={"location": _LOCATION, "mode": "annual"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"tilt_deg": 32.0, "azimuth_deg": 180.0, "poa_kwh_per_m2": 1500.0, "source": "pvgis"}


def test_analytics_losses(client: TestClient, sample_weather_raw: dict) -> None:
    mock_client = AsyncMock()
    mock_client.get_forecast.return_value = sample_weather_raw
    app.dependency_overrides[get_open_meteo_client] = lambda: mock_client

    try:
        response = client.post(
            "/api/analytics/losses", json={"location": _LOCATION, "array": _ARRAY, "horizon_hours": 24}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total_loss_pct"] >= 14.0
    assert set(body["named_losses_pct"]) == {
        "soiling",
        "shading",
        "wiring",
        "mismatch",
        "connections",
        "inverter",
        "availability",
    }


def test_analytics_earnings(client: TestClient) -> None:
    response = client.post("/api/analytics/earnings", json={"energy_kwh": 100.0, "price_per_kwh": 0.2})
    assert response.status_code == 200
    assert response.json() == {"energy_kwh": 100.0, "earnings": 20.0, "co2_avoided_kg": 40.0}
