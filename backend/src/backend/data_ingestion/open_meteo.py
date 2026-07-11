"""Open-Meteo forecast and historical-archive weather client.

Pure I/O: fetches hourly weather/irradiance and returns it as plain records.
No physics or business logic lives here.
"""

from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from backend.config import settings
from backend.data_ingestion.exceptions import DataSourceError

_TRANSIENT = (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)
_TIMEOUT = httpx.Timeout(10.0, connect=5.0, read=20.0)

_HOURLY_VARS = (
    "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m,wind_speed_10m,cloud_cover"
)


class OpenMeteoClient:
    """Async client for Open-Meteo's free weather APIs."""

    def __init__(self, base_url: str | None = None, archive_url: str | None = None) -> None:
        self._base_url = base_url or settings.open_meteo_base_url
        self._archive_url = archive_url or settings.open_meteo_archive_url

    @retry(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def get_forecast(self, latitude: float, longitude: float, forecast_days: int = 16) -> dict[str, Any]:
        """Fetch hourly forecast weather/irradiance for the next `forecast_days` days.

        Args:
            latitude: Site latitude, -90 to 90.
            longitude: Site longitude, -180 to 180.
            forecast_days: Days ahead to forecast, 1-16.

        Returns:
            Raw Open-Meteo JSON response with an `hourly` block.

        Raises:
            DataSourceError: If the request fails or returns no usable data.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": _HOURLY_VARS,
            "forecast_days": min(forecast_days, 16),
            "timezone": "UTC",
        }
        return await self._get(f"{self._base_url}/forecast", params)

    @retry(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def get_historical(self, latitude: float, longitude: float, start: date, end: date) -> dict[str, Any]:
        """Fetch hourly historical weather/irradiance for a date range.

        Args:
            latitude: Site latitude.
            longitude: Site longitude.
            start: Range start (inclusive).
            end: Range end (inclusive).

        Returns:
            Raw Open-Meteo archive JSON response with an `hourly` block.

        Raises:
            DataSourceError: If the request fails or returns no usable data.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": _HOURLY_VARS,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "timezone": "UTC",
        }
        return await self._get(f"{self._archive_url}/archive", params)

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as e:
            raise DataSourceError("open-meteo", f"HTTP {e.response.status_code}") from e
        except _TRANSIENT as e:
            raise DataSourceError("open-meteo", "connection failed") from e

        if "hourly" not in data:
            raise DataSourceError("open-meteo", "response missing 'hourly' block")
        return data
