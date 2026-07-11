"""Rolling mean absolute error, computed from the same (modeled, actual) day
pairs used for bias correction.

Known simplification (Section 6.2 of the dev plan): this is model error
against actual production on days already elapsed, not true lead-time
forecast error — a real deployment would track error separately per forecast
horizon. Good enough to derive a "how far off has this site's model been"
uncertainty band.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MAEResult:
    """Mean absolute error between modeled and logged-actual daily production.

    Args:
        mae_kwh: Mean absolute error, in kWh/day.
        mae_pct: mae_kwh as a fraction of mean actual production (0.1 = 10%).
        n_days: Number of day-pairs the error is based on.
    """

    mae_kwh: float
    mae_pct: float
    n_days: int


def compute_mae(modeled_actual_kwh_pairs: list[tuple[float, float]]) -> MAEResult:
    """Compute rolling MAE from paired (modeled, actual) daily kWh.

    Returns:
        MAEResult with all-zero fields if no pairs are given.
    """
    if not modeled_actual_kwh_pairs:
        return MAEResult(mae_kwh=0.0, mae_pct=0.0, n_days=0)

    errors = [abs(a - m) for m, a in modeled_actual_kwh_pairs]
    mean_actual = sum(a for _, a in modeled_actual_kwh_pairs) / len(modeled_actual_kwh_pairs)
    mae_kwh = sum(errors) / len(errors)
    mae_pct = mae_kwh / mean_actual if mean_actual > 0 else 0.0
    return MAEResult(mae_kwh=round(mae_kwh, 3), mae_pct=round(mae_pct, 4), n_days=len(modeled_actual_kwh_pairs))
