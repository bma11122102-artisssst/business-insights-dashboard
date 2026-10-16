import numpy as np
import pandas as pd

from vaultdata.analytics.inventory import demand_outlook


def _df_with_trend(increasing: bool, n_days=60):
    idx = pd.date_range("2024-01-01", periods=n_days, freq="D")
    base = np.linspace(1, 10, n_days) if increasing else np.linspace(10, 1, n_days)
    rows = []
    for date, qty in zip(idx, base):
        rows.append({"Date": date, "Product line": "Widgets", "Quantity": max(1, round(qty)), "Total": qty * 10})
    return pd.DataFrame(rows)


def test_demand_outlook_flags_increasing_trend_as_stockout_risk():
    df = _df_with_trend(increasing=True)
    outlook = demand_outlook(df, horizon_days=14)
    assert len(outlook) == 1
    assert outlook[0].risk == "Potential stockout risk"
    assert outlook[0].trend_direction == "Increasing"


def test_demand_outlook_flags_decreasing_trend_as_overstock_risk():
    df = _df_with_trend(increasing=False)
    outlook = demand_outlook(df, horizon_days=14)
    assert outlook[0].risk == "Potential overstock risk"
    assert outlook[0].trend_direction == "Decreasing"


def test_demand_outlook_empty_when_no_product_line_column():
    df = pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=5), "Quantity": range(5), "Total": range(5)})
    assert demand_outlook(df) == []


def test_demand_outlook_handles_flat_demand_as_balanced():
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    df = pd.DataFrame({"Date": idx, "Product line": "Widgets", "Quantity": [5] * 30, "Total": [50.0] * 30})
    outlook = demand_outlook(df, horizon_days=14)
    assert outlook[0].risk == "Balanced demand outlook"
    assert outlook[0].trend_direction == "Stable"


def test_demand_outlook_covers_multiple_product_lines():
    a = _df_with_trend(increasing=True)
    b = _df_with_trend(increasing=False)
    b["Product line"] = "Gadgets"
    df = pd.concat([a, b], ignore_index=True)
    outlook = demand_outlook(df, horizon_days=7)
    assert {o.product_line for o in outlook} == {"Widgets", "Gadgets"}
