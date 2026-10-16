"""Global filters, shared consistently across every page.

`apply_filters` is a pure function (easy to unit test); `render_filters`
is the thin Streamlit sidebar wrapper around it. Filter selections live in
st.session_state so they persist as a visitor moves between pages.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

FILTER_STATE_KEY = "vaultdata_filters"


@dataclass
class FilterState:
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None = None
    product_lines: list[str] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    customer_types: list[str] = field(default_factory=list)
    genders: list[str] = field(default_factory=list)
    payments: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    filtered = df
    if state.date_range:
        start, end = state.date_range
        filtered = filtered[(filtered["Date"] >= pd.Timestamp(start)) & (filtered["Date"] <= pd.Timestamp(end))]
    if state.product_lines and "Product line" in filtered.columns:
        filtered = filtered[filtered["Product line"].isin(state.product_lines)]
    if state.branches and "Branch" in filtered.columns:
        filtered = filtered[filtered["Branch"].isin(state.branches)]
    if state.customer_types and "Customer type" in filtered.columns:
        filtered = filtered[filtered["Customer type"].isin(state.customer_types)]
    if state.genders and "Gender" in filtered.columns:
        filtered = filtered[filtered["Gender"].isin(state.genders)]
    if state.payments and "Payment" in filtered.columns:
        filtered = filtered[filtered["Payment"].isin(state.payments)]
    if state.regions and "Region" in filtered.columns:
        filtered = filtered[filtered["Region"].isin(state.regions)]
    if state.channels and "Channel" in filtered.columns:
        filtered = filtered[filtered["Channel"].isin(state.channels)]
    return filtered


def _multiselect(label: str, df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    options = sorted(df[column].dropna().unique().tolist())
    return st.sidebar.multiselect(label, options, default=[], key=f"filter_{column}")


def _reset_filters():
    for key in list(st.session_state):
        if key.startswith("filter_") or key == FILTER_STATE_KEY:
            del st.session_state[key]


def render_filters(df: pd.DataFrame) -> FilterState:
    identity = str(df.attrs.get('source', 'other')) + str(df["Date"].min()) + str(df["Date"].max())
    if st.session_state.get('_filter_dataset') != identity:
        _reset_filters()
        st.session_state['_filter_dataset'] = identity
    st.sidebar.markdown("**Filters**")

    date_range = None
    if "Date" in df.columns and df["Date"].notna().any():
        min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
        picked = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="filter_dates")
        if isinstance(picked, tuple) and len(picked) == 2:
            date_range = picked
        else:
            st.sidebar.info("Choose both a start and end date.")
            st.stop()

    state = FilterState(
        date_range=date_range,
        product_lines=_multiselect("Category", df, "Product line"),
        branches=_multiselect("Branch", df, "Branch"),
        customer_types=_multiselect("Customer group", df, "Customer type"),
        genders=_multiselect("Gender", df, "Gender"),
        payments=_multiselect("Payment method", df, "Payment"),
        regions=_multiselect("Region", df, "Region"),
        channels=_multiselect("Channel", df, "Channel"),
    )
    st.session_state[FILTER_STATE_KEY] = state

    st.sidebar.button("Reset filters", on_click=_reset_filters)

    return state
