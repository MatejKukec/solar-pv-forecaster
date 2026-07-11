"""Tests for backend.calibration.bias and backend.calibration.mae."""

import pytest

from backend.calibration.bias import MIN_DAYS_FOR_CALIBRATION, apply_bias, compute_bias
from backend.calibration.mae import compute_mae


def test_compute_bias_below_threshold_returns_uncalibrated() -> None:
    pairs = [(10.0, 9.0)] * (MIN_DAYS_FOR_CALIBRATION - 1)
    result = compute_bias(pairs)
    assert result.is_calibrated is False
    assert result.factor == 1.0


def test_compute_bias_at_threshold_is_calibrated() -> None:
    pairs = [(10.0, 8.0)] * MIN_DAYS_FOR_CALIBRATION
    result = compute_bias(pairs)
    assert result.is_calibrated is True
    assert result.factor == pytest.approx(0.8)


def test_compute_bias_skips_zero_modeled_pairs() -> None:
    pairs = [(10.0, 8.0)] * MIN_DAYS_FOR_CALIBRATION + [(0.0, 5.0)]
    result = compute_bias(pairs)
    assert result.n_days == MIN_DAYS_FOR_CALIBRATION
    assert result.is_calibrated is True


def test_compute_bias_no_pairs_returns_uncalibrated() -> None:
    result = compute_bias([])
    assert result == compute_bias([])
    assert result.n_days == 0
    assert result.is_calibrated is False


def test_apply_bias_scales_modeled_value() -> None:
    pairs = [(10.0, 8.0)] * MIN_DAYS_FOR_CALIBRATION
    bias = compute_bias(pairs)
    assert apply_bias(20.0, bias) == pytest.approx(16.0)


def test_apply_bias_clamps_to_non_negative() -> None:
    pairs = [(10.0, -1.0)] * MIN_DAYS_FOR_CALIBRATION
    bias = compute_bias(pairs)
    assert apply_bias(20.0, bias) == 0.0


def test_compute_mae_no_pairs_returns_zeros() -> None:
    result = compute_mae([])
    assert result.mae_kwh == 0.0
    assert result.mae_pct == 0.0
    assert result.n_days == 0


def test_compute_mae_computes_absolute_error() -> None:
    pairs = [(10.0, 8.0), (10.0, 12.0)]  # errors: 2, 2 -> mean 2
    result = compute_mae(pairs)
    assert result.mae_kwh == pytest.approx(2.0)
    assert result.n_days == 2


def test_compute_mae_pct_relative_to_mean_actual() -> None:
    pairs = [(10.0, 10.0), (10.0, 20.0)]  # errors: 0, 10 -> mean 5; mean actual 15
    result = compute_mae(pairs)
    assert result.mae_kwh == pytest.approx(5.0)
    assert result.mae_pct == pytest.approx(5.0 / 15.0, rel=1e-3)


def test_compute_mae_zero_actual_avoids_division_by_zero() -> None:
    result = compute_mae([(5.0, 0.0)])
    assert result.mae_pct == 0.0
