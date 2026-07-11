"""Forecast routes: hourly/daily PV power forecast."""

from datetime import UTC, datetime
from typing import cast

import pandas as pd
import structlog
from fastapi import APIRouter, HTTPException

from backend.api.deps import OpenMeteoDep, SessionDep
from backend.calibration import compute_mae
from backend.calibration.service import gather_modeled_actual_pairs
from backend.data_ingestion import DataSourceError
from backend.models import Location, PVArray
from backend.physics_engine import forecast_ac_power
from backend.schemas import ForecastRequest, ForecastResponse, HourlyPowerPoint

router = APIRouter(prefix="/api/forecast", tags=["forecast"])
logger = structlog.get_logger()


@router.post("")
async def get_forecast(request: ForecastRequest, weather_client: OpenMeteoDep, session: SessionDep) -> ForecastResponse:
    """Return an hourly AC power forecast, aggregated across all arrays at the site.

    Each hour also gets an `uncertainty_kw` band (± MAE% of that hour's
    output), derived from the site's historical model error once it has
    enough logged production (see calibration.mae). Zero/None until then.

    Args:
        request: Location, array configs, and forecast horizon.
        weather_client: Injected Open-Meteo client.
        session: DB session, used to look up this site's production history.

    Returns:
        Hourly forecast points with total AC power per hour.

    Raises:
        HTTPException: 502 if the upstream weather provider fails.
    """
    location = Location(
        latitude=request.location.latitude,
        longitude=request.location.longitude,
        elevation_m=request.location.elevation_m,
        timezone=request.location.timezone,
    )
    forecast_days = max(1, min(16, (request.horizon_hours + 23) // 24))

    try:
        weather_raw = await weather_client.get_forecast(location.latitude, location.longitude, forecast_days)
    except DataSourceError as e:
        logger.warning("weather_fetch_failed", source=e.source, error=str(e))
        raise HTTPException(status_code=502, detail=f"weather provider unavailable: {e}") from e

    total_kw_by_hour: dict[datetime, float] = {}
    ghi_by_hour: dict[datetime, float] = {}
    cloud_by_hour: dict[datetime, float] = {}
    arrays = []

    for array_in in request.arrays:
        array = PVArray(
            capacity_kw=array_in.capacity_kw,
            tilt_deg=array_in.tilt_deg,
            azimuth_deg=array_in.azimuth_deg,
            location=location,
            system_loss_pct=array_in.system_loss_pct,
        )
        arrays.append(array)
        power_df = forecast_ac_power(weather_raw, location, array)
        power_df = power_df.head(request.horizon_hours)

        for raw_ts, row in power_df.iterrows():
            ts = cast(pd.Timestamp, raw_ts)
            total_kw_by_hour[ts] = total_kw_by_hour.get(ts, 0.0) + float(row["ac_power_kw"])
            ghi_by_hour[ts] = float(row["ghi"])
            cloud_by_hour[ts] = float(row["cloud_cover"])

    pairs = await gather_modeled_actual_pairs(weather_client, session, location, arrays)
    mae = compute_mae(pairs)

    hourly = [
        HourlyPowerPoint(
            timestamp=ts,
            ac_power_kw=round(power, 3),
            ghi_w_m2=ghi_by_hour.get(ts),
            cloud_cover_pct=cloud_by_hour.get(ts),
            uncertainty_kw=round(power * mae.mae_pct, 3) if mae.n_days > 0 else None,
        )
        for ts, power in sorted(total_kw_by_hour.items())
    ]

    return ForecastResponse(
        location=request.location,
        generated_at=datetime.now(UTC),
        hourly=hourly,
        total_capacity_kw=sum(a.capacity_kw for a in request.arrays),
        mae_pct=mae.mae_pct,
        is_calibrated=mae.n_days > 0,
    )
