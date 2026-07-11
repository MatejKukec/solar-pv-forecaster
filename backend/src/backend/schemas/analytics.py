"""Request/response schemas for the analytics endpoints (tilt, losses, earnings)."""

from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.common import ArrayIn, LocationIn


class TiltRequest(BaseModel):
    """Request for optimal fixed-tilt guidance.

    Args:
        mode: "current"/"daily" run a single-day clear-sky simulation for
            `target_date` (defaults to today). "annual" prefers PVGIS's
            typical-year optimum, falling back to a 12-sample-day simulation.
        target_date: ISO date, used by "current"/"daily" mode.
    """

    location: LocationIn
    mode: Literal["current", "daily", "annual"] = "annual"
    target_date: str | None = Field(default=None, description="ISO date, e.g. 2025-03-14")


class TiltResponse(BaseModel):
    """Recommended fixed tilt/azimuth."""

    tilt_deg: float
    azimuth_deg: float
    poa_kwh_per_m2: float
    source: str


class LossRequest(BaseModel):
    """Request for a loss breakdown, using forecast weather over the horizon."""

    location: LocationIn
    array: ArrayIn
    horizon_hours: int = Field(default=24, ge=1, le=360)


class LossResponse(BaseModel):
    """Named loss breakdown plus dynamic temperature-driven loss."""

    named_losses_pct: dict[str, float]
    temperature_loss_pct: float
    total_loss_pct: float


class EarningsRequest(BaseModel):
    """Request for earnings/CO2-avoided estimates from a known energy total."""

    energy_kwh: float = Field(ge=0, le=10_000_000)
    price_per_kwh: float = Field(ge=0, le=10)
    grid_co2_kg_per_kwh: float | None = Field(default=None, ge=0, le=2)


class EarningsResponse(BaseModel):
    """Earnings and CO2 avoided for a given amount of generated energy."""

    energy_kwh: float
    earnings: float
    co2_avoided_kg: float
