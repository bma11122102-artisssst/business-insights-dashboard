"""Inventory intelligence: demand outlook derived from historical sales
velocity, per product line.

This dataset contains sales transactions, not stock-on-hand or reorder
records -- there is no real inventory data to predict against. Everything
in this module is therefore an **illustrative inventory scenario**: demand
is inferred from historical units sold, and "risk" reflects the direction
and stability of that demand trend, not an actual stockout or overstock
event. This label is carried through to the UI (views/inventory_intelligence.py)
verbatim, per the product's own honesty requirement.

Method: with ~1,000 transactions split across 6 product lines and 89 days,
per-product daily quantity is too sparse (often 0-3 units/day) to support a
seasonal model -- fitting weekly seasonality here would be overfitting noise,
not signal. Instead this uses an ordinary-least-squares trend line over daily
(zero-filled) demand, which is a defensible way to read direction and rate of
change from a short, sparse series without pretending to more precision than
the data supports.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

STOCKOUT_THRESHOLD = 1.20  # forecast demand >=20% above recent average
OVERSTOCK_THRESHOLD = 0.80  # forecast demand <=20% below recent average
TREND_NOISE_THRESHOLD = 0.05  # ignore slopes explaining <5% relative change over the window

RISK_ACTIONS = {
    "Potential stockout risk": (
        "Forecast demand is trending above recent average velocity. "
        "Suggested action: review procurement and replenishment planning to keep "
        "pace with rising demand."
    ),
    "Potential overstock risk": (
        "Forecast demand is trending below recent average velocity. "
        "Suggested action: review order quantities to avoid excess stock and "
        "tied-up working capital."
    ),
    "Balanced demand outlook": (
        "Forecast demand is broadly in line with recent average velocity. "
        "Suggested action: maintain current replenishment cadence."
    ),
}


@dataclass
class ProductDemandForecast:
    product_line: str
    observed_total_units: int
    observed_avg_daily_demand: float
    forecast_daily_demand: float
    forecast_horizon_units: float
    trend_direction: str
    risk: str
    suggested_action: str


def _daily_demand_series(df: pd.DataFrame, product_line: str) -> pd.Series:
    subset = df[df["Product line"] == product_line]
    daily = subset.groupby(subset["Date"].dt.normalize())["Quantity"].sum()
    full_index = pd.date_range(df["Date"].min().normalize(), df["Date"].max().normalize(), freq="D")
    return daily.reindex(full_index, fill_value=0)


def _trend_forecast(daily: pd.Series, horizon_days: int) -> tuple[float, str]:
    x = np.arange(len(daily))
    y = daily.values.astype(float)
    if len(x) < 2 or np.all(y == y[0]):
        slope, intercept = 0.0, float(y.mean()) if len(y) else 0.0
    else:
        slope, intercept = np.polyfit(x, y, 1)

    forecast_x = len(daily) + horizon_days / 2
    forecast_daily = max(0.0, float(intercept + slope * forecast_x))

    mean_demand = float(y.mean()) if len(y) else 0.0
    relative_slope = abs(slope * len(daily)) / mean_demand if mean_demand > 0 else 0.0
    if relative_slope < TREND_NOISE_THRESHOLD:
        trend_direction = "Stable"
    else:
        trend_direction = "Increasing" if slope > 0 else "Decreasing"

    return forecast_daily, trend_direction


def demand_outlook(df: pd.DataFrame, horizon_days: int = 14) -> list[ProductDemandForecast]:
    """One illustrative demand forecast per product line present in `df`."""
    if "Product line" not in df.columns or df.empty:
        return []

    results: list[ProductDemandForecast] = []
    for product_line in sorted(df["Product line"].dropna().unique()):
        daily = _daily_demand_series(df, product_line)
        observed_avg = float(daily.mean())
        forecast_daily, trend_direction = _trend_forecast(daily, horizon_days)

        if observed_avg > 0 and forecast_daily >= observed_avg * STOCKOUT_THRESHOLD:
            risk = "Potential stockout risk"
        elif observed_avg > 0 and forecast_daily <= observed_avg * OVERSTOCK_THRESHOLD:
            risk = "Potential overstock risk"
        else:
            risk = "Balanced demand outlook"

        results.append(
            ProductDemandForecast(
                product_line=product_line,
                observed_total_units=int(daily.sum()),
                observed_avg_daily_demand=observed_avg,
                forecast_daily_demand=forecast_daily,
                forecast_horizon_units=forecast_daily * horizon_days,
                trend_direction=trend_direction,
                risk=risk,
                suggested_action=RISK_ACTIONS[risk],
            )
        )

    results.sort(key=lambda r: r.forecast_horizon_units, reverse=True)
    return results
