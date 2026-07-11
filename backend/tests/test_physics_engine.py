"""Tests for backend.physics_engine.pv_model."""

import pandas as pd
import pytest

from backend.models import Location, PVArray
from backend.physics_engine.pv_model import (
    compute_poa_irradiance,
    forecast_ac_power,
    get_clearsky,
    parse_open_meteo_hourly,
)


def test_parse_open_meteo_hourly_returns_expected_columns(sample_weather_raw: dict) -> None:
    df = parse_open_meteo_hourly(sample_weather_raw)
    assert list(df.columns) == ["ghi", "dni", "dhi", "temp_air", "wind_speed", "cloud_cover"]
    assert len(df) == 24


def test_parse_open_meteo_hourly_missing_hourly_block_raises() -> None:
    with pytest.raises(ValueError, match="missing 'hourly.time'"):
        parse_open_meteo_hourly({})


def test_forecast_ac_power_is_zero_at_night(
    sample_weather_raw: dict, sample_location: Location, sample_array: PVArray
) -> None:
    result = forecast_ac_power(sample_weather_raw, sample_location, sample_array)
    midnight = result.iloc[0]
    assert midnight["ac_power_kw"] == pytest.approx(0.0, abs=1e-6)


def test_forecast_ac_power_peaks_near_solar_noon(
    sample_weather_raw: dict, sample_location: Location, sample_array: PVArray
) -> None:
    result = forecast_ac_power(sample_weather_raw, sample_location, sample_array)
    peak_hour = result["ac_power_kw"].idxmax()
    assert 9 <= peak_hour.hour <= 15


def test_forecast_ac_power_never_exceeds_capacity(
    sample_weather_raw: dict, sample_location: Location, sample_array: PVArray
) -> None:
    result = forecast_ac_power(sample_weather_raw, sample_location, sample_array)
    assert (result["ac_power_kw"] <= sample_array.capacity_kw).all()


def test_forecast_ac_power_empty_weather_raises(sample_location: Location, sample_array: PVArray) -> None:
    empty = {"hourly": {"time": []}}
    with pytest.raises(ValueError, match="no hourly weather data"):
        forecast_ac_power(empty, sample_location, sample_array)


@pytest.mark.parametrize("tilt_deg,azimuth_deg", [(0, 180), (30, 180), (30, 90), (90, 180)])
def test_compute_poa_irradiance_handles_various_orientations(
    sample_weather_raw: dict, sample_location: Location, tilt_deg: float, azimuth_deg: float
) -> None:
    weather = parse_open_meteo_hourly(sample_weather_raw)
    array = PVArray(capacity_kw=5.0, tilt_deg=tilt_deg, azimuth_deg=azimuth_deg, location=sample_location)
    poa = compute_poa_irradiance(weather, sample_location, array)
    assert (poa >= 0).all()


def test_get_clearsky_returns_ghi_dni_dhi(sample_location: Location) -> None:
    times = pd.date_range("2026-07-09 00:00", periods=24, freq="h", tz="UTC")
    clearsky = get_clearsky(times, sample_location)
    assert {"ghi", "dni", "dhi"}.issubset(clearsky.columns)
    assert (clearsky["ghi"] >= 0).all()
