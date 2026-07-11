"""Tests for backend.analytics (tilt, losses, earnings)."""

from datetime import date
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from backend.analytics.earnings import estimate_earnings
from backend.analytics.losses import breakdown_losses
from backend.analytics.tilt import optimal_tilt_annual, optimal_tilt_for_day
from backend.data_ingestion import DataSourceError, PVGISClient
from backend.models import Location


def test_optimal_tilt_for_day_prefers_equator_facing_azimuth() -> None:
    location = Location(latitude=45.8, longitude=16.0)
    result = optimal_tilt_for_day(location, date(2026, 6, 21))
    assert result.azimuth_deg == 180.0  # northern hemisphere -> south-facing
    assert 0 <= result.tilt_deg <= 90
    assert result.source == "clearsky-simulation"


def test_optimal_tilt_for_day_southern_hemisphere_faces_north() -> None:
    location = Location(latitude=-33.9, longitude=18.4)
    result = optimal_tilt_for_day(location, date(2026, 6, 21))
    assert result.azimuth_deg == 0.0


@pytest.mark.asyncio
async def test_optimal_tilt_annual_uses_pvgis_when_available() -> None:
    location = Location(latitude=45.8, longitude=16.0)
    pvgis_client = AsyncMock(spec=PVGISClient)
    pvgis_client.get_optimal_angles.return_value = {
        "inputs": {"mounting_system": {"fixed": {"slope": {"value": 34}, "azimuth": {"value": 0}}}},
        "outputs": {"totals": {"fixed": {"E_y": 1234.5}}},
    }
    result = await optimal_tilt_annual(location, pvgis_client, 2026)
    assert result.source == "pvgis"
    assert result.tilt_deg == 34.0
    assert result.azimuth_deg == 180.0  # PVGIS 0=south -> compass 180
    assert result.poa_kwh_per_m2 == 1234.5


@pytest.mark.asyncio
async def test_optimal_tilt_annual_falls_back_to_clearsky_on_no_coverage() -> None:
    location = Location(latitude=45.8, longitude=16.0)
    pvgis_client = AsyncMock(spec=PVGISClient)
    pvgis_client.get_optimal_angles.side_effect = DataSourceError("pvgis", "out of coverage")
    result = await optimal_tilt_annual(location, pvgis_client, 2026)
    assert result.source == "clearsky-simulation"
    assert 0 <= result.tilt_deg <= 90


@pytest.mark.asyncio
async def test_optimal_tilt_annual_falls_back_on_unexpected_shape() -> None:
    location = Location(latitude=45.8, longitude=16.0)
    pvgis_client = AsyncMock(spec=PVGISClient)
    pvgis_client.get_optimal_angles.return_value = {"unexpected": "shape"}
    result = await optimal_tilt_annual(location, pvgis_client, 2026)
    assert result.source == "clearsky-simulation"


def test_breakdown_losses_sums_to_total() -> None:
    cell_temp = pd.Series([25.0, 35.0, 45.0])
    breakdown = breakdown_losses(system_loss_pct=14.0, cell_temp_c=cell_temp)
    assert breakdown.total_loss_pct == pytest.approx(14.0 + breakdown.temperature_loss_pct)
    assert sum(breakdown.named_losses_pct.values()) == pytest.approx(14.0)
    assert breakdown.temperature_loss_pct > 0  # avg cell temp above 25C


def test_breakdown_losses_no_temperature_loss_when_cool() -> None:
    cell_temp = pd.Series([10.0, 15.0, 20.0])
    breakdown = breakdown_losses(system_loss_pct=14.0, cell_temp_c=cell_temp)
    assert breakdown.temperature_loss_pct == 0.0


def test_breakdown_losses_empty_series() -> None:
    breakdown = breakdown_losses(system_loss_pct=14.0, cell_temp_c=pd.Series([], dtype=float))
    assert breakdown.temperature_loss_pct == 0.0
    assert breakdown.total_loss_pct == 14.0


def test_estimate_earnings_computes_earnings_and_co2() -> None:
    result = estimate_earnings(energy_kwh=100.0, price_per_kwh=0.2, grid_co2_kg_per_kwh=0.4)
    assert result.earnings == pytest.approx(20.0)
    assert result.co2_avoided_kg == pytest.approx(40.0)


def test_estimate_earnings_clamps_negative_energy() -> None:
    result = estimate_earnings(energy_kwh=-5.0, price_per_kwh=0.2)
    assert result.energy_kwh == 0.0
    assert result.earnings == 0.0
