"""Past-date route: historical reconstruction, bias-corrected, with actual overlay."""

from datetime import date as date_cls
from typing import cast

import pandas as pd
import structlog
from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.api.deps import OpenMeteoDep, SessionDep
from backend.calibration import apply_bias, compute_bias, compute_mae
from backend.calibration.service import gather_modeled_actual_pairs
from backend.data_ingestion import DataSourceError
from backend.models import Location, ProductionLog, PVArray
from backend.physics_engine import forecast_ac_power
from backend.schemas import HourlyPowerPoint, PastDateRequest, PastDateResponse
from backend.site_id import site_id_for

router = APIRouter(prefix="/api/past", tags=["past"])
logger = structlog.get_logger()


@router.post("")
async def get_past_date(
    request: PastDateRequest, weather_client: OpenMeteoDep, session: SessionDep
) -> PastDateResponse:
    """Reconstruct modeled output for a past date, bias-corrected, with any logged actual overlaid.

    Raises:
        HTTPException: 502 if the historical weather provider fails.
    """
    location = Location(
        latitude=request.location.latitude,
        longitude=request.location.longitude,
        elevation_m=request.location.elevation_m,
        timezone=request.location.timezone,
    )
    arrays = [
        PVArray(
            capacity_kw=a.capacity_kw,
            tilt_deg=a.tilt_deg,
            azimuth_deg=a.azimuth_deg,
            location=location,
            system_loss_pct=a.system_loss_pct,
        )
        for a in request.arrays
    ]
    target = date_cls.fromisoformat(request.date)

    try:
        weather_raw = await weather_client.get_historical(location.latitude, location.longitude, target, target)
    except DataSourceError as e:
        logger.warning("weather_fetch_failed", source=e.source, error=str(e))
        raise HTTPException(status_code=502, detail=f"weather provider unavailable: {e}") from e

    total_kw_by_hour: dict[pd.Timestamp, float] = {}
    modeled_kwh = 0.0
    for array in arrays:
        power_df = forecast_ac_power(weather_raw, location, array)
        modeled_kwh += float(power_df["ac_power_kw"].sum())
        for raw_ts, row in power_df.iterrows():
            ts = cast(pd.Timestamp, raw_ts)
            total_kw_by_hour[ts] = total_kw_by_hour.get(ts, 0.0) + float(row["ac_power_kw"])
    hourly = [
        HourlyPowerPoint(timestamp=ts, ac_power_kw=round(power, 3)) for ts, power in sorted(total_kw_by_hour.items())
    ]

    pairs = await gather_modeled_actual_pairs(weather_client, session, location, arrays, known={target: modeled_kwh})

    site_id = site_id_for(location.latitude, location.longitude)
    logged_today = session.exec(
        select(ProductionLog).where(ProductionLog.site_id == site_id, ProductionLog.production_date == target)
    ).first()
    actual_today = logged_today.actual_kwh if logged_today else None

    bias = compute_bias(pairs)
    mae = compute_mae(pairs)
    calibrated_kwh = apply_bias(modeled_kwh, bias)

    return PastDateResponse(
        date=request.date,
        location=request.location,
        hourly=hourly,
        modeled_kwh=round(modeled_kwh, 3),
        calibrated_kwh=round(calibrated_kwh, 3),
        actual_kwh=actual_today,
        bias_factor=round(bias.factor, 4),
        is_calibrated=bias.is_calibrated,
        mae_kwh=mae.mae_kwh,
        mae_pct=mae.mae_pct,
    )
