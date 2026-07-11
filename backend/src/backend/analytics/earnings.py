"""Earnings and CO2-avoided estimates from generated energy."""

from dataclasses import dataclass

# Rough global grid-average carbon intensity (kg CO2 per kWh) — used only
# when the caller doesn't supply a local figure.
DEFAULT_GRID_CO2_KG_PER_KWH = 0.4


@dataclass(frozen=True)
class EarningsResult:
    """Earnings and CO2 avoided for a given amount of generated energy."""

    energy_kwh: float
    earnings: float
    co2_avoided_kg: float


def estimate_earnings(
    energy_kwh: float,
    price_per_kwh: float,
    grid_co2_kg_per_kwh: float = DEFAULT_GRID_CO2_KG_PER_KWH,
) -> EarningsResult:
    """Estimate earnings and CO2 avoided for a given amount of generated energy.

    Args:
        energy_kwh: Total energy generated over the window (kWh). Negative
            values are clamped to 0.
        price_per_kwh: Local electricity price or feed-in tariff.
        grid_co2_kg_per_kwh: Grid carbon intensity displaced by this generation.

    Returns:
        EarningsResult with earnings in the same currency as price_per_kwh.
    """
    energy_kwh = max(0.0, energy_kwh)
    return EarningsResult(
        energy_kwh=round(energy_kwh, 3),
        earnings=round(energy_kwh * price_per_kwh, 2),
        co2_avoided_kg=round(energy_kwh * grid_co2_kg_per_kwh, 2),
    )
