from __future__ import annotations

import pandas as pd
import streamlit as st
from vaultdata.data.track4 import is_track4
from views.track4 import about

from vaultdata.config import APP_STATUS, BRAND_LINE


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    if is_track4(df_all):
        about(df_filtered, df_all)
        return
    st.header("About / Methodology")

    st.markdown(
        f"""
**{BRAND_LINE}.** A workspace for investigating business performance and supporting management decisions.

**Status: {APP_STATUS}.** This is a demonstration built on a public sample retail dataset —
it is not a live production system and does not process real business or customer data.
"""
    )

    st.subheader("Data")
    st.markdown(
        """
The demo dataset is a public 1,000-row supermarket transactions sample (one row per invoice,
January–March). It has no persistent customer identifier, no real inventory/stock-on-hand
records, and no currency label — figures are displayed in Indian rupees (₹) as requested,
without an exchange-rate conversion. You can also upload your own CSV from the sidebar; the app
maps common column-name variants (e.g. "sales"/"revenue"/"total" all map to the internal
"Total" field) and validates that the minimum required columns are present before running.
"""
    )

    st.subheader("Customer Intelligence — why not RFM?")
    st.markdown(
        """
Classic RFM (Recency, Frequency, Monetary value) requires linking multiple transactions to
the same customer over time. This dataset provides no customer identifier capable of that —
every row is an independent transaction. Rather than simulate a fake customer ID to force an
RFM analysis, the Customer Intelligence page segments **transactions** on spend, basket size,
and satisfaction instead, and says so explicitly. Segment labels (e.g. "High-Value Baskets")
are derived programmatically from each cluster's own computed averages relative to the overall
dataset — never assigned by hand — and the K-Means k is chosen by silhouette score rather than
fixed in advance.
"""
    )

    st.subheader("Forecasting")
    st.markdown(
        """
Sales forecasting uses Holt-Winters exponential smoothing (additive trend + weekly
seasonality), fit on daily revenue. This is a defensible choice for a short (~89-day) daily
series with a plausible weekly cycle and no external regressors — heavier methods (SARIMA,
ML-based) would not be better-justified on data this size and would risk overfitting. Forecasts
are validated on a **time-ordered** holdout (never a random split, which would leak future
information into training for a time series) and reported with MAE/RMSE/MAPE. Confidence
intervals come from the model's own innovations-based simulation, not a fabricated fixed band.
"""
    )

    st.subheader("Inventory Intelligence")
    st.markdown(
        """
This dataset contains sales transactions, not stock-on-hand or reorder data — there is no real
inventory to predict. The Inventory Intelligence page is explicitly labeled an **illustrative
inventory scenario**: it fits a trend line to each product line's historical daily units sold
and flags whether forecast demand is trending meaningfully above or below its recent average.
An earlier version of this project trained a regression model to predict `Quantity` from
features that were an almost-exact algebraic function of `Quantity` itself (`Total` and
`Unit price`) — a form of data leakage that produced a near-perfect but meaningless score. That
model was removed and replaced with this trend-based approach.
"""
    )

    st.subheader("Limitations")
    st.markdown(
        """
- Single-source, sample data — not validated against a live business.
- No true customer-level history; segmentation is transaction-level.
- No real inventory, cost, or lead-time data; inventory outputs are illustrative only.
- Forecast uncertainty grows with horizon length and is wider than the chart's shaded band
  might suggest for horizons long relative to the ~89 days of available history.
- Recommendations are analytical suggestions generated from the current data selection, not
  guaranteed business outcomes.
"""
    )
