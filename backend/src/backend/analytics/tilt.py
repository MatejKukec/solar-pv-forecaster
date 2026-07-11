"""Optimal fixed-tilt guidance.

"current"/"daily" modes run a clear-sky simulation for a single day —
PVGIS only has a typical-year answer, not a day-specific one. "annual" mode
prefers PVGIS's typical-year optimum (it's the literal purpose of that
endpoint) and falls back to a 12-sample-day clear-sky simulation if PVGIS
has no coverage at this location or returns an unexpected shape.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import pvlib

from backend.data_ingestion import DataSourceError, PVGISClient
from backend.models import Location

_TILT_CANDIDATES_DEG = range(0, 91, 5)


@dataclass(frozen=True)
class TiltResult:
    """Recommended fixed tilt/azimuth and the insolation it yields.

    Args:
        tilt_deg: Recommended panel tilt from horizontal.
        azimuth_deg: Recommended azimuth, compass convention (180 = south).
        poa_kwh_per_m2: Plane-of-array insolation over the evaluated window.
        source: "pvgis" or "clearsky-simulation", for transparency in the UI.
    """

    tilt_deg: float
    azimuth_deg: float
    poa_kwh_per_m2: float
    source: str


def _equator_facing_azimuth(latitude: float) -> float:
    """South (180°) in the northern hemisphere, north (0°) in the southern."""
    return 180.0 if latitude >= 0 else 0.0


def _best_tilt_for_days(location: Location, days: list[date]) -> TiltResult:
    """Brute-force the tilt in `_TILT_CANDIDATES_DEG` that maximizes total
    clear-sky POA irradiance summed across the given days, at a fixed
    equator-facing azimuth."""
    azimuth = _equator_facing_azimuth(location.latitude)
    site = pvlib.location.Location(location.latitude, location.longitude, altitude=location.elevation_m)

    times = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") + pd.Timedelta(hours=h) for d in days for h in range(24)])
    clearsky = site.get_clearsky(times, model="ineichen")
    solar_position = site.get_solarposition(times)

    best_tilt, best_poa_wh = 0.0, -1.0
    for tilt in _TILT_CANDIDATES_DEG:
        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            solar_zenith=solar_position["apparent_zenith"],
            solar_azimuth=solar_position["azimuth"],
            dni=clearsky["dni"],
            ghi=clearsky["ghi"],
            dhi=clearsky["dhi"],
        )
        total_wh = float(poa["poa_global"].sum())
        if total_wh > best_poa_wh:
            best_tilt, best_poa_wh = float(tilt), total_wh

    return TiltResult(
        tilt_deg=best_tilt, azimuth_deg=azimuth, poa_kwh_per_m2=best_poa_wh / 1000, source="clearsky-simulation"
    )


def optimal_tilt_for_day(location: Location, target_date: date) -> TiltResult:
    """Best fixed tilt for a single day ("current" or "daily" mode)."""
    return _best_tilt_for_days(location, [target_date])


async def optimal_tilt_annual(location: Location, pvgis_client: PVGISClient, year: int) -> TiltResult:
    """Best fixed tilt for a typical year ("annual" mode)."""
    try:
        raw = await pvgis_client.get_optimal_angles(location.latitude, location.longitude)
        mounting = raw["inputs"]["mounting_system"]["fixed"]
        pvgis_azimuth = float(mounting["azimuth"]["value"])  # PVGIS convention: 0 = south
        return TiltResult(
            tilt_deg=float(mounting["slope"]["value"]),
            azimuth_deg=(pvgis_azimuth + 180.0) % 360,
            poa_kwh_per_m2=float(raw["outputs"]["totals"]["fixed"]["E_y"]),
            source="pvgis",
        )
    except (DataSourceError, KeyError, TypeError, ValueError):
        sample_days = [date(year, month, 15) for month in range(1, 13)]
        return _best_tilt_for_days(location, sample_days)
