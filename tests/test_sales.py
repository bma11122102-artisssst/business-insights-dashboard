import pandas as pd
import pytest

from vaultdata.analytics.sales import compute_kpis, product_performance, revenue_trend


def _sample_df():
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]),
            "Total": [100.0, 50.0, 30.0],
            "Quantity": [2, 1, 3],
            "Product line": ["A", "B", "A"],
            "Rating": [8.0, 6.0, 9.0],
        }
    )


def test_compute_kpis_basic():
    df = _sample_df()
    kpis = compute_kpis(df)
    assert kpis.total_revenue == 180.0
    assert kpis.total_transactions == 3
    assert kpis.units_sold == 6
    assert kpis.avg_transaction_value == pytest.approx(60.0)
    assert kpis.top_product_line == "A"
    assert kpis.revenue_growth_pct is None  # no full_df given


def test_compute_kpis_empty_df_does_not_crash():
    df = _sample_df().iloc[0:0]
    kpis = compute_kpis(df)
    assert kpis.total_revenue == 0.0
    assert kpis.total_transactions == 0
    assert kpis.top_product_line is None


def test_revenue_growth_uses_prior_period_when_available():
    full = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "Total": [100.0, 100.0, 150.0, 150.0],
            "Quantity": [1, 1, 1, 1],
            "Product line": ["A"] * 4,
        }
    )
    current = full[full["Date"] >= "2024-01-03"]
    kpis = compute_kpis(current, full_df=full)
    assert kpis.revenue_growth_pct == pytest.approx(50.0)


def test_revenue_growth_none_without_prior_data():
    full = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "Total": [100.0, 150.0],
            "Quantity": [1, 1],
            "Product line": ["A", "A"],
        }
    )
    kpis = compute_kpis(full, full_df=full)
    assert kpis.revenue_growth_pct is None


def test_product_performance_ranks_by_revenue():
    df = _sample_df()
    perf = product_performance(df)
    assert list(perf.index)[0] == "A"  # A has 130 revenue vs B's 50
    assert perf.loc["A", "Revenue"] == 130.0


def test_revenue_trend_resamples_daily():
    df = _sample_df()
    trend = revenue_trend(df, freq="D")
    assert trend.loc[pd.Timestamp("2024-01-01")] == 150.0
    assert trend.loc[pd.Timestamp("2024-01-02")] == 30.0
