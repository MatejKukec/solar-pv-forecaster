"""Forecast endpoint request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import ArrayIn, LocationIn


class ForecastRequest(BaseModel):
    """Request body for hourly/daily power forecasts.

    Args:
        location: Site coordinates.
        arrays: 1-5 PV arrays at this site.
        horizon_hours: Forecast horizon in hours, up to 360 (15 days).
    """

    location: LocationIn
    arrays: list[ArrayIn] = Field(min_length=1, max_length=5)
    horizon_hours: int = Field(default=48, ge=1, le=360)

    @field_validator("arrays")
    @classmethod
    def require_at_least_one_array(cls, v: list[ArrayIn]) -> list[ArrayIn]:
        if not v:
            raise ValueError("at least one array is required")
        return v


class HourlyPowerPoint(BaseModel):
    """Modeled or forecast power output for a single hour."""

    timestamp: datetime
    ac_power_kw: float
    ghi_w_m2: float | None = None
    cloud_cover_pct: float | None = None
    uncertainty_kw: float | None = None


class ForecastResponse(BaseModel):
    """Hourly power forecast for a site, aggregated across all arrays.

    Args:
        mae_pct: The site's historical model error (see calibration.mae),
            used to derive `uncertainty_kw` on each hourly point. 0.0 until
            the site has enough logged production history.
        is_calibrated: Whether mae_pct is based on real history.
    """

    location: LocationIn
    generated_at: datetime
    hourly: list[HourlyPowerPoint]
    total_capacity_kw: float
    mae_pct: float = 0.0
    is_calibrated: bool = False


class PastDateRequest(BaseModel):
    """Request body for historical/past-date power reconstruction."""

    location: LocationIn
    arrays: list[ArrayIn] = Field(min_length=1, max_length=5)
    date: str = Field(description="ISO date, e.g. 2025-03-14")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        from datetime import date as date_cls

        try:
            date_cls.fromisoformat(v)
        except ValueError as e:
            raise ValueError("date must be in YYYY-MM-DD format") from e
        return v


class PastDateResponse(BaseModel):
    """Modeled reconstruction for a past date, bias-corrected and overlaid with any logged actual.

    Args:
        modeled_kwh: Raw physics-model estimate for the day, uncorrected.
        calibrated_kwh: modeled_kwh with the site's bias factor applied (equals
            modeled_kwh when the site isn't calibrated yet).
        actual_kwh: Logged actual production for this date, if the user logged it.
        bias_factor: The site's current bias factor (1.0 if not yet calibrated).
        is_calibrated: Whether the site has enough logged history to be calibrated.
    """

    date: str
    location: LocationIn
    hourly: list[HourlyPowerPoint]
    modeled_kwh: float
    calibrated_kwh: float
    actual_kwh: float | None
    bias_factor: float
    is_calibrated: bool
    mae_kwh: float
    mae_pct: float
