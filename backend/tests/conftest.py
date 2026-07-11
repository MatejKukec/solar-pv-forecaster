"""Shared test fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from backend.api.deps import get_session
from backend.main import app
from backend.models import Location, PVArray


@pytest.fixture
def sample_location() -> Location:
    return Location(latitude=45.815, longitude=15.9819, elevation_m=158.0, timezone="Europe/Zagreb")


@pytest.fixture
def sample_array(sample_location: Location) -> PVArray:
    return PVArray(capacity_kw=5.0, tilt_deg=30.0, azimuth_deg=180.0, location=sample_location)


@pytest.fixture
def sample_weather_raw() -> dict:
    """24 hourly points mimicking an Open-Meteo forecast response."""
    times = [f"2026-07-09T{h:02d}:00" for h in range(24)]
    # Rough noon-peaked irradiance curve, zero at night.
    ghi = [0, 0, 0, 0, 0, 20, 100, 250, 420, 580, 700, 780, 800, 780, 700, 580, 420, 250, 100, 20, 0, 0, 0, 0]
    return {
        "hourly": {
            "time": times,
            "shortwave_radiation": ghi,
            "direct_normal_irradiance": [v * 1.1 for v in ghi],
            "diffuse_radiation": [v * 0.3 for v in ghi],
            "temperature_2m": [22.0] * 24,
            "wind_speed_10m": [3.0] * 24,
            "cloud_cover": [10.0] * 24,
        }
    }


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A TestClient wired to a fresh, empty SQLite DB per test.

    Isolated from the app's real database (and its auto-seeded demo data,
    see backend.seed) so tests stay deterministic regardless of run order.
    """
    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    def override_get_session() -> Iterator[Session]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_session, None)
