"""Shared request/response schemas used across API routes."""

from pydantic import BaseModel, Field, field_validator


class LocationIn(BaseModel):
    """Geographic coordinates supplied by the client."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float = Field(default=0.0, ge=-500, le=9000)
    timezone: str = Field(default="UTC", max_length=64)


class ArrayIn(BaseModel):
    """A single PV array's configuration, as supplied by the client."""

    capacity_kw: float = Field(gt=0, le=10_000)
    tilt_deg: float = Field(ge=0, le=90)
    azimuth_deg: float = Field(ge=0, le=360)
    system_loss_pct: float = Field(default=14.0, ge=0, le=50)

    @field_validator("azimuth_deg")
    @classmethod
    def normalize_azimuth(cls, v: float) -> float:
        return v % 360


class ErrorDetail(BaseModel):
    """Structured error body returned on 4xx/5xx responses."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Top-level error envelope."""

    error: ErrorDetail
