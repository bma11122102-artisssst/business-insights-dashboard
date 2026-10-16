"""Sales forecasting: Holt-Winters exponential smoothing.

Why Holt-Winters rather than something heavier (SARIMA/Prophet/ML): this
dataset has ~89 daily points with a plausible weekly cycle and no exogenous
regressors. Holt-Winters (additive trend + additive weekly seasonality) is a
well-established, defensible method for exactly this shape of short daily
series, and it directly supports both a real point forecast and simulated
prediction intervals -- unlike the app's previous approach of running
`seasonal_decompose`, which only decomposes history and produces no future
values at all.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from vaultdata.config import FORECAST_SEASONAL_PERIOD, FORECAST_TEST_HOLDOUT_DAYS

METHOD_LABEL = "Holt-Winters exponential smoothing (additive trend + weekly seasonality)"


class ForecastError(Exception):
    """Raised when the data doesn't support forecasting -- message is
    written to be shown to a user directly."""


@dataclass
class ForecastValidation:
    mae: float
    rmse: float
    mape: float | None
    holdout_days: int


@dataclass
class ForecastResult:
    history: pd.Series
    forecast: pd.Series
    lower: pd.Series
    upper: pd.Series
    horizon_days: int
    method: str = METHOD_LABEL
    validation: ForecastValidation | None = None


def _min_required_days(seasonal_period: int) -> int:
    return 2 * seasonal_period + 7  # two full seasonal cycles plus a small margin


def _fit(series: pd.Series, seasonal_period: int) -> ExponentialSmoothing:
    return ExponentialSmoothing(
        series,
        trend="add",
        seasonal="add",
        seasonal_periods=seasonal_period,
        initialization_method="estimated",
    ).fit(optimized=True)


def validate_forecast(
    series: pd.Series,
    seasonal_period: int = FORECAST_SEASONAL_PERIOD,
    holdout_days: int = FORECAST_TEST_HOLDOUT_DAYS,
) -> ForecastValidation | None:
    """Time-ordered (not random) train/test split: fits on all but the last
    `holdout_days`, forecasts that many days forward, and compares to the
    actual held-out values. Returns None if there isn't enough history for a
    meaningful holdout -- never a fabricated metric."""
    min_needed = _min_required_days(seasonal_period) + holdout_days
    if len(series) < min_needed:
        return None

    train, test = series.iloc[:-holdout_days], series.iloc[-holdout_days:]
    fitted = _fit(train, seasonal_period)
    predicted = fitted.forecast(holdout_days)

    errors = test.values - predicted.values
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    nonzero_mask = test.values != 0
    mape = float(np.mean(np.abs(errors[nonzero_mask] / test.values[nonzero_mask])) * 100) if nonzero_mask.any() else None

    return ForecastValidation(mae=mae, rmse=rmse, mape=mape, holdout_days=holdout_days)


def forecast_future(
    series: pd.Series,
    horizon_days: int,
    seasonal_period: int = FORECAST_SEASONAL_PERIOD,
    interval_width: float = 0.80,
    n_simulations: int = 300,
) -> ForecastResult:
    """Fits on the full series and forecasts `horizon_days` ahead, with
    simulated prediction intervals (statsmodels' own innovations-based
    simulation, not a fabricated +/-X% band)."""
    if len(series) < _min_required_days(seasonal_period):
        raise ForecastError(
            f"Forecasting requires at least {_min_required_days(seasonal_period)} days of daily "
            f"history with a valid date column and numeric sales measure; this selection has "
            f"{len(series)}."
        )

    fitted = _fit(series, seasonal_period)
    point_forecast = fitted.forecast(horizon_days)

    rng = np.random.default_rng(42)
    # statsmodels renamed this kwarg from `random_state` to `rng` around 0.15;
    # detect which one the installed version expects rather than pinning an
    # exact version or leaving a deprecation warning in normal operation.
    seed_kwarg = "rng" if "rng" in inspect.signature(fitted.simulate).parameters else "random_state"
    simulations = fitted.simulate(nsimulations=horizon_days, repetitions=n_simulations, **{seed_kwarg: rng})
    lower_q = (1 - interval_width) / 2
    upper_q = 1 - lower_q
    lower = simulations.quantile(lower_q, axis=1)
    upper = simulations.quantile(upper_q, axis=1)

    validation = validate_forecast(series, seasonal_period)

    return ForecastResult(
        history=series,
        forecast=point_forecast,
        lower=lower,
        upper=upper,
        horizon_days=horizon_days,
        validation=validation,
    )
