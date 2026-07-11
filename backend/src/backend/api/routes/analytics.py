"""Analytics routes: optimal tilt guidance, loss breakdown, earnings/CO2 avoided."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException

from backend.analytics import (
    DEFAULT_GRID_CO2_KG_PER_KWH,
    breakdown_losses,
    estimate_earnings,
    optimal_tilt_annual,
    optimal_tilt_for_day,
)
from backend.api.deps import OpenMeteoDep, PVGISDep
from backend.data_ingestion import DataSourceError
from backend.models import Location, PVArray
from backend.physics_engine import compute_cell_temperature, parse_open_meteo_hourly
from backend.schemas import EarningsRequest, EarningsResponse, LossRequest, LossResponse, TiltRequest, TiltResponse

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/tilt")
async def get_optimal_tilt(request: TiltRequest, pvgis_client: PVGISDep) -> TiltResponse:
    """Recommend a fixed tilt/azimuth for the site, per the requested mode."""
    location = Location(
        latitude=request.location.latitude,
        longitude=request.location.longitude,
        elevation_m=request.location.elevation_m,
    )
    target = date.fromisoformat(request.target_date) if request.target_date else datetime.now(UTC).date()

    if request.mode == "annual":
        result = await optimal_tilt_annual(location, pvgis_client, target.year)
    else:
        result = optimal_tilt_for_day(location, target)

    return TiltResponse(
        tilt_deg=result.tilt_deg,
        azimuth_deg=result.azimuth_deg,
        poa_kwh_per_m2=round(result.poa_kwh_per_m2, 3),
        source=result.source,
    )


@router.post("/losses")
async def get_loss_breakdown(request: LossRequest, weather_client: OpenMeteoDep) -> LossResponse:
    """Break a lumped system loss down into named categories plus dynamic temperature loss.

    Raises:
        HTTPException: 502 if the upstream weather provider fails.
    """
    location = Location(latitude=request.location.latitude, longitude=request.location.longitude)
    array = PVArray(
        capacity_kw=request.array.capacity_kw,
        tilt_deg=request.array.tilt_deg,
        azimuth_deg=request.array.azimuth_deg,
        location=location,
        system_loss_pct=request.array.system_loss_pct,
    )
    forecast_days = max(1, min(16, (request.horizon_hours + 23) // 24))

    try:
        weather_raw = await weather_client.get_forecast(location.latitude, location.longitude, forecast_days)
    except DataSourceError as e:
        raise HTTPException(status_code=502, detail=f"weather provider unavailable: {e}") from e

    weather = parse_open_meteo_hourly(weather_raw).head(request.horizon_hours)
    cell_temp = compute_cell_temperature(weather, location, array)
    breakdown = breakdown_losses(array.system_loss_pct, cell_temp)

    return LossResponse(
        named_losses_pct=breakdown.named_losses_pct,
        temperature_loss_pct=breakdown.temperature_loss_pct,
        total_loss_pct=breakdown.total_loss_pct,
    )


@router.post("/earnings")
def get_earnings(request: EarningsRequest) -> EarningsResponse:
    """Estimate earnings and CO2 avoided for a given amount of generated energy."""
    result = estimate_earnings(
        request.energy_kwh,
        request.price_per_kwh,
        request.grid_co2_kg_per_kwh if request.grid_co2_kg_per_kwh is not None else DEFAULT_GRID_CO2_KG_PER_KWH,
    )
    return EarningsResponse(
        energy_kwh=result.energy_kwh, earnings=result.earnings, co2_avoided_kg=result.co2_avoided_kg
    )
