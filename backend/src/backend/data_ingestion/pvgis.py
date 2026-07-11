"""PVGIS (EU JRC) client — typical-year solar resource and optimal-angle data."""

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from backend.config import settings
from backend.data_ingestion.exceptions import DataSourceError

_TRANSIENT = (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)
_TIMEOUT = httpx.Timeout(10.0, connect=5.0, read=20.0)


class PVGISClient:
    """Async client for the PVGIS `PVcalc` and `seriescalc` endpoints."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.pvgis_base_url

    @retry(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def get_optimal_angles(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Fetch PVGIS's estimated optimal fixed tilt/azimuth for a location.

        Args:
            latitude: Site latitude.
            longitude: Site longitude.

        Returns:
            Raw PVGIS JSON with `mounting_system.fixed.slope` / `.azimuth`.

        Raises:
            DataSourceError: If the request fails or PVGIS has no coverage here.
        """
        params: dict[str, str | int | float] = {
            "lat": latitude,
            "lon": longitude,
            "peakpower": 1,
            "loss": 14,
            "optimalangles": 1,
            "outputformat": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(f"{self._base_url}/PVcalc", params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as e:
            raise DataSourceError("pvgis", f"HTTP {e.response.status_code} (likely out of coverage)") from e
        except _TRANSIENT as e:
            raise DataSourceError("pvgis", "connection failed") from e

        if "inputs" not in data:
            raise DataSourceError("pvgis", "response missing 'inputs' block")
        return data
