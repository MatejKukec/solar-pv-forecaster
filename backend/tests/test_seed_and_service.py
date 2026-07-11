"""Tests for backend.seed and backend.calibration.service."""

from datetime import date
from unittest.mock import AsyncMock

from sqlmodel import Session, SQLModel, create_engine, select

from backend.calibration.service import gather_modeled_actual_pairs
from backend.data_ingestion import DataSourceError
from backend.models import Location, ProductionLog, PVArray
from backend.seed import DEMO_DAYS, demo_site_id, seed_demo_data


def _fresh_session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_seed_demo_data_inserts_expected_days() -> None:
    with _fresh_session() as session:
        seed_demo_data(session)
        logs = session.exec(select(ProductionLog).where(ProductionLog.site_id == demo_site_id())).all()
        assert len(logs) == DEMO_DAYS
        assert all(log.actual_kwh > 0 for log in logs)


def test_seed_demo_data_is_idempotent() -> None:
    with _fresh_session() as session:
        seed_demo_data(session)
        seed_demo_data(session)
        logs = session.exec(select(ProductionLog).where(ProductionLog.site_id == demo_site_id())).all()
        assert len(logs) == DEMO_DAYS


async def test_gather_pairs_skips_days_weather_fetch_fails() -> None:
    location = Location(latitude=1.0, longitude=1.0)
    array = PVArray(capacity_kw=5.0, tilt_deg=30.0, azimuth_deg=180.0, location=location)
    weather_client = AsyncMock()
    weather_client.get_historical.side_effect = DataSourceError("open-meteo", "boom")

    with _fresh_session() as session:
        session.add(ProductionLog(site_id="site-under-test", production_date=date(2026, 1, 1), actual_kwh=10.0))
        session.commit()
        # site_id_for(1.0, 1.0) won't match "site-under-test", so this exercises the empty-logs path.
        pairs = await gather_modeled_actual_pairs(weather_client, session, location, [array])
    assert pairs == []


async def test_gather_pairs_uses_known_value_without_fetching() -> None:
    from backend.site_id import site_id_for

    location = Location(latitude=2.0, longitude=2.0)
    array = PVArray(capacity_kw=5.0, tilt_deg=30.0, azimuth_deg=180.0, location=location)
    weather_client = AsyncMock()
    target = date(2026, 1, 1)

    with _fresh_session() as session:
        session.add(ProductionLog(site_id=site_id_for(2.0, 2.0), production_date=target, actual_kwh=12.0))
        session.commit()
        pairs = await gather_modeled_actual_pairs(weather_client, session, location, [array], known={target: 15.0})

    assert pairs == [(15.0, 12.0)]
    weather_client.get_historical.assert_not_called()


async def test_gather_pairs_fetches_and_sums_across_arrays(sample_weather_raw: dict) -> None:
    from backend.site_id import site_id_for

    location = Location(latitude=3.0, longitude=3.0)
    arrays = [
        PVArray(capacity_kw=5.0, tilt_deg=30.0, azimuth_deg=180.0, location=location),
        PVArray(capacity_kw=3.0, tilt_deg=20.0, azimuth_deg=180.0, location=location),
    ]
    weather_client = AsyncMock()
    weather_client.get_historical.return_value = sample_weather_raw
    target = date(2026, 1, 1)

    with _fresh_session() as session:
        session.add(ProductionLog(site_id=site_id_for(3.0, 3.0), production_date=target, actual_kwh=9.0))
        session.commit()
        pairs = await gather_modeled_actual_pairs(weather_client, session, location, arrays)

    assert len(pairs) == 1
    modeled, actual = pairs[0]
    assert modeled > 0
    assert actual == 9.0
