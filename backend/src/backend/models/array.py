"""Domain entities for PV arrays and sites."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """Geographic coordinates for a site."""

    latitude: float
    longitude: float
    elevation_m: float = 0.0
    timezone: str = "UTC"


@dataclass(frozen=True)
class PVArray:
    """A single PV array's physical configuration.

    Args:
        capacity_kw: DC nameplate capacity in kW.
        tilt_deg: Panel tilt from horizontal, 0-90.
        azimuth_deg: Panel azimuth, 0=N, 90=E, 180=S, 270=W.
        location: Site coordinates.
    """

    capacity_kw: float
    tilt_deg: float
    azimuth_deg: float
    location: Location
    system_loss_pct: float = 14.0
