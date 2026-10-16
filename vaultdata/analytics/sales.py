"""Sales intelligence: KPIs and business-question-driven aggregations.

Every function here takes a plain DataFrame and returns plain
pandas/Python objects -- no Streamlit calls -- so these are directly
unit-testable and reusable by both the Executive Overview and Sales
Intelligence pages.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class KPISet:
    total_revenue: float
    total_transactions: int
    units_sold: int
    avg_transaction_value: float
    top_product_line: str | None
    top_product_line_revenue: float | None
    avg_rating: float | None
    revenue_growth_pct: float | None  # None when a prior period can't be computed


def compute_kpis(df: pd.DataFrame, full_df: pd.DataFrame | None = None) -> KPISet:
    """Computes headline KPIs for `df` (the currently filtered slice).

    `full_df`, if given, is the *unfiltered* dataset -- used only to look up
    the immediately-preceding period of equal length for a period-over-period
    revenue growth figure. Growth is None (never fabricated) when there isn't
    enough prior data to compute it.
    """
    total_revenue = float(df["Total"].sum())
    total_transactions = int(len(df))
    units_sold = int(df["Quantity"].sum())
    avg_transaction_value = float(df["Total"].mean()) if total_transactions else 0.0

    top_product_line = None
    top_product_line_revenue = None
    if "Product line" in df.columns and not df.empty:
        by_line = df.groupby("Product line")["Total"].sum().sort_values(ascending=False)
        if not by_line.empty:
            top_product_line = str(by_line.index[0])
            top_product_line_revenue = float(by_line.iloc[0])

    avg_rating = float(df["Rating"].mean()) if "Rating" in df.columns and not df.empty else None

    revenue_growth_pct = _period_over_period_growth(df, full_df)

    return KPISet(
        total_revenue=total_revenue,
        total_transactions=total_transactions,
        units_sold=units_sold,
        avg_transaction_value=avg_transaction_value,
        top_product_line=top_product_line,
        top_product_line_revenue=top_product_line_revenue,
        avg_rating=avg_rating,
        revenue_growth_pct=revenue_growth_pct,
    )


def _period_over_period_growth(df: pd.DataFrame, full_df: pd.DataFrame | None) -> float | None:
    if full_df is None or df.empty or "Date" not in df.columns:
        return None
    start, end = df["Date"].min(), df["Date"].max()
    span_days = (end - start).days + 1
    prior_end = start - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=span_days - 1)
    if full_df["Date"].min() > prior_start or full_df["Date"].max() < prior_end:
        return None

    prior_slice = full_df[(full_df["Date"] >= prior_start) & (full_df["Date"] <= prior_end)]
    if prior_slice.empty:
        return None  # no prior-period data available -- don't fabricate a comparison

    current_revenue = df["Total"].sum()
    prior_revenue = prior_slice["Total"].sum()
    if prior_revenue == 0:
        return None
    return float(100 * (current_revenue - prior_revenue) / prior_revenue)


def revenue_trend(df: pd.DataFrame, freq: str = "D") -> pd.Series:
    """Revenue over time at the given pandas offset alias (e.g. 'D', 'W')."""
    series = df.set_index("Date")["Total"].resample(freq).sum()
    series.name = "Revenue"
    return series


def product_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Ranks product lines by revenue, units, and average transaction value."""
    grouped = df.groupby("Product line").agg(
        Revenue=("Total", "sum"),
        Units=("Quantity", "sum"),
        Transactions=("Total", "count"),
    )
    grouped["Avg Transaction Value"] = grouped["Revenue"] / grouped["Transactions"]
    grouped["Revenue Share %"] = 100 * grouped["Revenue"] / grouped["Revenue"].sum()
    return grouped.sort_values("Revenue", ascending=False)


def branch_performance(df: pd.DataFrame) -> pd.DataFrame | None:
    if "Branch" not in df.columns:
        return None
    grouped = df.groupby("Branch").agg(
        Revenue=("Total", "sum"),
        Transactions=("Total", "count"),
        **({"City": ("City", "first")} if "City" in df.columns else {}),
    )
    grouped["Avg Transaction Value"] = grouped["Revenue"] / grouped["Transactions"]
    return grouped.sort_values("Revenue", ascending=False)


def payment_behavior(df: pd.DataFrame) -> pd.DataFrame | None:
    if "Payment" not in df.columns:
        return None
    grouped = df.groupby("Payment").agg(Revenue=("Total", "sum"), Transactions=("Total", "count"))
    grouped["Share %"] = 100 * grouped["Transactions"] / grouped["Transactions"].sum()
    return grouped.sort_values("Revenue", ascending=False)


def customer_type_breakdown(df: pd.DataFrame) -> pd.DataFrame | None:
    if "Customer type" not in df.columns:
        return None
    grouped = df.groupby("Customer type").agg(
        Revenue=("Total", "sum"),
        Transactions=("Total", "count"),
        **({"Avg Rating": ("Rating", "mean")} if "Rating" in df.columns else {}),
    )
    grouped["Avg Transaction Value"] = grouped["Revenue"] / grouped["Transactions"]
    return grouped.sort_values("Revenue", ascending=False)


def time_of_day_pattern(df: pd.DataFrame) -> pd.DataFrame | None:
    if "Hour" not in df.columns or df["Hour"].isna().all():
        return None
    grouped = df.groupby("Hour").agg(Revenue=("Total", "sum"), Transactions=("Total", "count"))
    return grouped.sort_index()


def weekday_pattern(df: pd.DataFrame) -> pd.DataFrame | None:
    if "Weekday" not in df.columns:
        return None
    grouped = df.groupby("Weekday").agg(Revenue=("Total", "sum"), Transactions=("Total", "count"))
    return grouped.reindex([d for d in WEEKDAY_ORDER if d in grouped.index])
