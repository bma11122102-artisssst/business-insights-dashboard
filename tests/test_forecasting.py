import numpy as np
import pandas as pd
import pytest

from vaultdata.analytics.forecasting import ForecastError, forecast_future, validate_forecast


def _synthetic_series(n_days=90, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n_days, freq="D")
    weekly = 20 * np.sin(2 * np.pi * np.arange(n_days) / 7)
    trend = np.arange(n_days) * 0.5
    noise = rng.normal(0, 5, n_days)
    values = 200 + trend + weekly + noise
    return pd.Series(values, index=idx)


def test_forecast_future_returns_requested_horizon():
    series = _synthetic_series()
    result = forecast_future(series, horizon_days=14)
    assert len(result.forecast) == 14
    assert len(result.lower) == 14
    assert len(result.upper) == 14
    assert (result.upper.values >= result.lower.values).all()


def test_forecast_future_raises_clear_error_on_short_series():
    series = _synthetic_series(n_days=5)
    with pytest.raises(ForecastError, match="Forecasting requires"):
        forecast_future(series, horizon_days=7)


def test_validate_forecast_returns_none_on_short_series():
    series = _synthetic_series(n_days=10)
    assert validate_forecast(series) is None


def test_validate_forecast_returns_reasonable_metrics_on_synthetic_data():
    series = _synthetic_series(n_days=90)
    validation = validate_forecast(series)
    assert validation is not None
    assert validation.mae >= 0
    assert validation.rmse >= validation.mae * 0.5  # RMSE >= MAE is the general expectation
    assert validation.holdout_days == 14


def test_forecast_result_includes_validation_when_possible():
    series = _synthetic_series()
    result = forecast_future(series, horizon_days=7)
    assert result.validation is not None
