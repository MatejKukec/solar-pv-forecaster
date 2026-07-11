"""Bias-correction: compares modeled vs. logged-actual production per site.

Simplified scope (Section 6.3 of the dev plan): a single multiplicative bias
factor per site, gated on at least 7 days of logged production. No held-out
validation or overfitting checks — that's explicitly cut for the demo.
"""

from dataclasses import dataclass

MIN_DAYS_FOR_CALIBRATION = 7


@dataclass(frozen=True)
class BiasResult:
    """Outcome of a bias-correction calculation for a site.

    Args:
        factor: Multiply modeled output by this to bias-correct it. 1.0 means
            no correction (either perfectly calibrated, or not yet gated).
        n_days: Number of (modeled, actual) day-pairs the factor is based on.
        is_calibrated: True once `n_days >= MIN_DAYS_FOR_CALIBRATION`.
    """

    factor: float
    n_days: int
    is_calibrated: bool


def compute_bias(modeled_actual_kwh_pairs: list[tuple[float, float]]) -> BiasResult:
    """Compute a site's bias factor from paired (modeled, actual) daily kWh.

    Args:
        modeled_actual_kwh_pairs: One (modeled_kwh, actual_kwh) pair per
            logged day. Pairs where modeled_kwh <= 0 are skipped — they'd
            produce an undefined ratio (e.g. a data gap).

    Returns:
        BiasResult with factor=1.0 and is_calibrated=False if fewer than
        MIN_DAYS_FOR_CALIBRATION usable pairs are available.
    """
    usable = [(m, a) for m, a in modeled_actual_kwh_pairs if m > 0]
    if len(usable) < MIN_DAYS_FOR_CALIBRATION:
        return BiasResult(factor=1.0, n_days=len(usable), is_calibrated=False)

    ratios = [a / m for m, a in usable]
    factor = sum(ratios) / len(ratios)
    return BiasResult(factor=factor, n_days=len(usable), is_calibrated=True)


def apply_bias(modeled_kwh: float, bias: BiasResult) -> float:
    """Apply a site's bias factor to a modeled value, clamped to non-negative."""
    return max(0.0, modeled_kwh * bias.factor)
