"""NASA POWER client — fallback solar resource source outside PVGIS coverage."""

from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from backend.config import settings
from backend.data_ingestion.exceptions import DataSourceError

_TRANSIENT = (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)
_TIMEOUT = httpx.Timeout(10.0, connect=5.0, read=20.0)


class NASAPowerClient:
    """Async client for NASA POWER's daily point API (global coverage)."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.nasa_power_base_url

    @retry(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def get_daily_irradiance(self, latitude: float, longitude: float, start: date, end: date) -> dict[str, Any]:
        """Fetch daily all-sky surface shortwave irradiance for a location/range.

        Args:
            latitude: Site latitude.
            longitude: Site longitude.
            start: Range start (inclusive).
            end: Range end (inclusive).

        Returns:
            Raw NASA POWER JSON with a `properties.parameter` block.

        Raises:
            DataSourceError: If the request fails or returns no usable data.
        """
        params: dict[str, str | int | float] = {
            "parameters": "ALLSKY_SFC_SW_DWN",
            "community": "RE",
            "latitude": latitude,
            "longitude": longitude,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(f"{self._base_url}/daily/point", params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as e:
            raise DataSourceError("nasa-power", f"HTTP {e.response.status_code}") from e
        except _TRANSIENT as e:
            raise DataSourceError("nasa-power", "connection failed") from e

        if "properties" not in data:
            raise DataSourceError("nasa-power", "response missing 'properties' block")
        return data
