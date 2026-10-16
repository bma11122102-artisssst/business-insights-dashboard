from __future__ import annotations

import pandas as pd
import streamlit as st

from vaultdata.analytics.sales import (
    branch_performance,
    customer_type_breakdown,
    payment_behavior,
    product_performance,
    time_of_day_pattern,
    weekday_pattern,
)
from vaultdata.viz.charts import ranking_bar_chart, revenue_trend_chart, weekday_hour_heatmap
from vaultdata.viz.formatting import format_currency
from vaultdata.data.track4 import is_track4, completed
from views.track4 import investigation
from vaultdata.viz.labels import readable_table


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    st.header("Sales")
    st.caption("Revenue trends, product performance, and where/when/how customers buy.")
    if is_track4(df_all):
        investigation(df_filtered)
        st.divider()
        st.subheader("Completed sales analysis")
        st.caption("Charts below count completed orders only. The files do not specify a currency.")
        df_filtered = completed(df_filtered)

    if df_filtered.empty:
        st.warning("No transactions match the current filters. Adjust the filters in the sidebar.")
        return

    st.subheader("Revenue trend")
    granularity = st.radio("Group by", ["Daily", "Weekly"], horizontal=True)
    freq = "D" if granularity == "Daily" else "W"
    trend = df_filtered.set_index("Date")["Total"].resample(freq).sum()
    st.plotly_chart(revenue_trend_chart(trend, f"{granularity} revenue"), use_container_width=True)

    st.divider()
    st.subheader("Product performance")
    perf = product_performance(df_filtered)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(ranking_bar_chart(perf, "Revenue", "Revenue by product line", "Revenue (₹)"), use_container_width=True)
    with c2:
        st.plotly_chart(ranking_bar_chart(perf, "Units", "Units sold by product line", "Units"), use_container_width=True)
    st.dataframe(
        readable_table(perf).style.format({"Revenue": lambda v: format_currency(v, suffix=False), "Average order value": lambda v: format_currency(v, suffix=False), "Share of revenue (%)": "{:.1f}%"}),
        use_container_width=True,
    )

    branch_df = branch_performance(df_filtered)
    if branch_df is not None:
        st.divider()
        st.subheader("Branch performance")
        st.plotly_chart(ranking_bar_chart(branch_df, "Revenue", "Revenue by branch", "Revenue (₹)"), use_container_width=True)

    c3, c4 = st.columns(2)
    payment_df = payment_behavior(df_filtered)
    if payment_df is not None:
        with c3:
            st.subheader("Payment behavior")
            st.plotly_chart(ranking_bar_chart(payment_df, "Revenue", "Revenue by payment method", "Revenue (₹)"), use_container_width=True)

    customer_df = customer_type_breakdown(df_filtered)
    if customer_df is not None:
        with c4:
            st.subheader("Customer type")
            st.plotly_chart(ranking_bar_chart(customer_df, "Revenue", "Revenue by customer type", "Revenue (₹)"), use_container_width=True)

    weekday_df = weekday_pattern(df_filtered)
    hour_df = time_of_day_pattern(df_filtered)
    if weekday_df is not None and hour_df is not None and "Hour" in df_filtered.columns:
        st.divider()
        st.subheader("Time-of-day / weekday pattern")
        st.plotly_chart(weekday_hour_heatmap(df_filtered), use_container_width=True)
    elif weekday_df is not None:
        st.divider()
        st.subheader("Weekday pattern")
        st.plotly_chart(ranking_bar_chart(weekday_df, "Revenue", "Revenue by weekday", "Revenue (₹)"), use_container_width=True)
