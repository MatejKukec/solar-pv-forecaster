"""Calibration routes: log actual production, check a site's calibration status.

The bias *factor* itself (the ratio that actually corrects a forecast) is
computed on demand in `/api/past`, where it's paired with a specific array
config. These routes just persist logged production and report how many
days a site has — enough for the UI to show calibration progress.
"""

from datetime import date as date_cls

from fastapi import APIRouter
from sqlmodel import select

from backend.api.deps import SessionDep
from backend.calibration import MIN_DAYS_FOR_CALIBRATION
from backend.models import ProductionLog
from backend.schemas import (
    CalibrationStatusResponse,
    ProductionHistoryEntry,
    ProductionHistoryResponse,
    ProductionLogIn,
    ProductionLogResponse,
)
from backend.site_id import site_id_for

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


@router.post("/production")
def log_production(entry: ProductionLogIn, session: SessionDep) -> ProductionLogResponse:
    """Log a day's actual production for a site, keyed by location."""
    site_id = site_id_for(entry.location.latitude, entry.location.longitude)
    row = ProductionLog(
        site_id=site_id, production_date=date_cls.fromisoformat(entry.date), actual_kwh=entry.actual_kwh
    )
    session.add(row)
    session.commit()

    n_days = session.exec(select(ProductionLog).where(ProductionLog.site_id == site_id)).all()
    return ProductionLogResponse(
        site_id=site_id,
        date=entry.date,
        actual_kwh=entry.actual_kwh,
        n_days_logged=len(n_days),
        is_calibrated=len(n_days) >= MIN_DAYS_FOR_CALIBRATION,
    )


@router.get("/status")
def calibration_status(latitude: float, longitude: float, session: SessionDep) -> CalibrationStatusResponse:
    """Report how many days of production a site has logged."""
    site_id = site_id_for(latitude, longitude)
    logs = session.exec(select(ProductionLog).where(ProductionLog.site_id == site_id)).all()
    return CalibrationStatusResponse(
        site_id=site_id,
        n_days_logged=len(logs),
        is_calibrated=len(logs) >= MIN_DAYS_FOR_CALIBRATION,
        bias_factor=1.0,
    )


@router.get("/history")
def calibration_history(
    latitude: float, longitude: float, session: SessionDep, limit: int = 30
) -> ProductionHistoryResponse:
    """List a site's logged production, most recent first.

    A DB-only read (no weather re-fetch), unlike bias/MAE computation —
    cheap enough to call freely without pressuring the weather provider.
    """
    site_id = site_id_for(latitude, longitude)
    logs = session.exec(
        select(ProductionLog).where(ProductionLog.site_id == site_id).order_by(ProductionLog.production_date.desc())  # type: ignore[attr-defined]
    ).all()
    entries = [
        ProductionHistoryEntry(date=log.production_date.isoformat(), actual_kwh=log.actual_kwh) for log in logs[:limit]
    ]
    return ProductionHistoryResponse(
        site_id=site_id,
        entries=entries,
        n_days_logged=len(logs),
        is_calibrated=len(logs) >= MIN_DAYS_FOR_CALIBRATION,
    )
