"""Shared logic for gathering a site's (modeled, actual) day-pairs.

Used by both `/api/past` (to compute a bias-corrected reconstruction) and
`/api/forecast` (to derive an uncertainty band from historical error).

Known simplification: re-fetches historical weather for every logged day on
every call — fine at demo scope (a handful of logged days), see the past.py
module docstring.
"""

from datetime import date as date_cls

from sqlmodel import Session, select

from backend.data_ingestion import DataSourceError, OpenMeteoClient
from backend.models import Location, ProductionLog, PVArray
from backend.physics_engine import forecast_ac_power
from backend.site_id import site_id_for


async def modeled_kwh_for_date(
    weather_client: OpenMeteoClient, location: Location, arrays: list[PVArray], target: date_cls
) -> float:
    """Sum modeled AC energy (kWh) across all arrays for a single past date."""
    weather_raw = await weather_client.get_historical(location.latitude, location.longitude, target, target)
    return sum(float(forecast_ac_power(weather_raw, location, array)["ac_power_kw"].sum()) for array in arrays)


async def gather_modeled_actual_pairs(
    weather_client: OpenMeteoClient,
    session: Session,
    location: Location,
    arrays: list[PVArray],
    known: dict[date_cls, float] | None = None,
) -> list[tuple[float, float]]:
    """Gather (modeled, actual) kWh pairs for every day this site has logged.

    Args:
        weather_client: Historical-weather client.
        session: DB session.
        location: Site coordinates (used to derive the site ID).
        arrays: Array configuration to model against.
        known: Optional {date: modeled_kwh} of already-computed values (e.g.
            today's forecast run), to skip a redundant historical re-fetch.

    Returns:
        One (modeled_kwh, actual_kwh) pair per logged day whose weather could
        be fetched. Days that fail to fetch are skipped.
    """
    known = known or {}
    site_id = site_id_for(location.latitude, location.longitude)
    logs = session.exec(select(ProductionLog).where(ProductionLog.site_id == site_id)).all()

    pairs: list[tuple[float, float]] = []
    for log in logs:
        if log.production_date in known:
            pairs.append((known[log.production_date], log.actual_kwh))
            continue
        try:
            modeled = await modeled_kwh_for_date(weather_client, location, arrays, log.production_date)
        except DataSourceError:
            continue
        pairs.append((modeled, log.actual_kwh))
    return pairs
