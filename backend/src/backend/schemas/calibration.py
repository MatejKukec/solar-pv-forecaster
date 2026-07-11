"""Request/response schemas for logging actual production and calibration status."""

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import LocationIn


class ProductionLogIn(BaseModel):
    """A day's actual logged production for a site."""

    location: LocationIn
    date: str = Field(description="ISO date, e.g. 2025-03-14")
    actual_kwh: float = Field(ge=0, le=1_000_000)

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        from datetime import date as date_cls

        try:
            date_cls.fromisoformat(v)
        except ValueError as e:
            raise ValueError("date must be in YYYY-MM-DD format") from e
        return v


class ProductionLogResponse(BaseModel):
    """Confirmation of a logged production entry, plus updated calibration status."""

    site_id: str
    date: str
    actual_kwh: float
    n_days_logged: int
    is_calibrated: bool


class CalibrationStatusResponse(BaseModel):
    """A site's current bias-correction status."""

    site_id: str
    n_days_logged: int
    is_calibrated: bool
    bias_factor: float


class ProductionHistoryEntry(BaseModel):
    """One logged day, for the history list — no modeled comparison (that
    would require re-fetching historical weather per day; kept out to avoid
    hammering the weather provider's rate limit for a secondary view)."""

    date: str
    actual_kwh: float


class ProductionHistoryResponse(BaseModel):
    """A site's logged production history, most recent first."""

    site_id: str
    entries: list[ProductionHistoryEntry]
    n_days_logged: int
    is_calibrated: bool
