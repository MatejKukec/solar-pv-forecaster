"""System loss breakdown/diagnostics.

`PVArray.system_loss_pct` is a single lumped derate applied in the physics
pipeline. This splits that lump into named categories using typical
industry proportions (NREL's PVWatts default loss diagram), and computes
the temperature-driven derate separately and dynamically from actual/
forecast cell temperature — that one isn't lumped in, it depends on weather.
"""

from dataclasses import dataclass

import pandas as pd

# Relative shares of a PVWatts-style non-temperature loss derate.
# Source: NREL PVWatts default loss breakdown. Applied proportionally to
# whatever system_loss_pct the array is configured with.
_LOSS_SHARES = {
    "soiling": 0.20,
    "shading": 0.15,
    "wiring": 0.15,
    "mismatch": 0.10,
    "connections": 0.05,
    "inverter": 0.20,
    "availability": 0.15,
}


@dataclass(frozen=True)
class LossBreakdown:
    """A loss diagnostic, split into named categories plus temperature.

    Args:
        named_losses_pct: Non-temperature losses, allocated from
            `system_loss_pct` by typical share.
        temperature_loss_pct: Average temperature-driven derate over the
            evaluated window (only counted when cell temp > 25°C).
        total_loss_pct: named losses + temperature loss.
    """

    named_losses_pct: dict[str, float]
    temperature_loss_pct: float
    total_loss_pct: float


def breakdown_losses(system_loss_pct: float, cell_temp_c: pd.Series, gamma_pdc: float = -0.004) -> LossBreakdown:
    """Split a lumped system loss into named categories, plus dynamic temperature loss.

    Args:
        system_loss_pct: The array's lumped non-temperature loss (%).
        cell_temp_c: Modeled cell temperature series (°C) for the window.
        gamma_pdc: PVWatts temperature coefficient, %/°C as a decimal (negative).

    Returns:
        Named-category breakdown plus the dynamic temperature loss.
    """
    named = {name: round(system_loss_pct * share, 3) for name, share in _LOSS_SHARES.items()}

    if cell_temp_c.empty:
        temperature_loss_pct = 0.0
    else:
        derate = (gamma_pdc * (cell_temp_c - 25.0)).clip(upper=0.0)
        temperature_loss_pct = round(float(-derate.mean()) * 100, 3)

    return LossBreakdown(
        named_losses_pct=named,
        temperature_loss_pct=temperature_loss_pct,
        total_loss_pct=round(system_loss_pct + temperature_loss_pct, 3),
    )
