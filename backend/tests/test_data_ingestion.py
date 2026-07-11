"""Tests for backend.data_ingestion clients. All network calls are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.data_ingestion.exceptions import DataSourceError
from backend.data_ingestion.open_meteo import OpenMeteoClient
from backend.data_ingestion.pvgis import PVGISClient


def _mock_response(json_body: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError("error", request=MagicMock(), response=response)
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.mark.asyncio
async def test_open_meteo_get_forecast_success() -> None:
    client = OpenMeteoClient()
    body = {"hourly": {"time": ["2026-07-09T00:00"], "shortwave_radiation": [0]}}
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(body))):
        result = await client.get_forecast(45.8, 16.0)
    assert result == body


@pytest.mark.asyncio
async def test_open_meteo_get_forecast_missing_hourly_raises() -> None:
    client = OpenMeteoClient()
    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response({}))),
        pytest.raises(DataSourceError, match="missing 'hourly'"),
    ):
        await client.get_forecast(45.8, 16.0)


@pytest.mark.asyncio
async def test_open_meteo_http_error_raises_data_source_error() -> None:
    client = OpenMeteoClient()
    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response({}, status_code=500))),
        pytest.raises(DataSourceError, match="open-meteo"),
    ):
        await client.get_forecast(45.8, 16.0)


@pytest.mark.asyncio
async def test_pvgis_out_of_coverage_raises_data_source_error() -> None:
    client = PVGISClient()
    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response({}, status_code=400))),
        pytest.raises(DataSourceError, match="pvgis"),
    ):
        await client.get_optimal_angles(45.8, 16.0)


@pytest.mark.asyncio
async def test_pvgis_success() -> None:
    client = PVGISClient()
    body = {"inputs": {}, "outputs": {"solar_optimal_angles": {"opt_angle": 34}}}
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(body))):
        result = await client.get_optimal_angles(45.8, 16.0)
    assert result == body
