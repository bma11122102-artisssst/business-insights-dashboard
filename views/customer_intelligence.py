from __future__ import annotations

import pandas as pd
import streamlit as st
from vaultdata.data.track4 import is_track4
from views.track4 import customers

from vaultdata.analytics.customers import build_segmentation_features, segment_transactions
from vaultdata.viz.charts import segmentation_scatter
from vaultdata.viz.formatting import format_currency, format_percent


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    if is_track4(df_all):
        customers(df_filtered, df_all)
        return
    st.header("Customers")
    st.caption("Compare groups of similar purchases in this file.")

    st.info(
        "This file has no customer IDs, so we cannot tell whether the same person bought more "
        "than once. The groups below compare purchases by spending, number of items, and ratings. "
        "They are groups of purchases, not identified customers.",
        icon="ℹ️",
    )

    if len(df_filtered) < 10:
        st.warning("Segmentation needs at least 10 transactions in the current selection.")
        return

    result = segment_transactions(df_filtered)
    if result is None:
        st.warning("Not enough usable data to segment the current selection.")
        return

    st.caption(f"We found {result.k} groups of similar purchases using spending and basket details.")
    with st.expander("How these groups were chosen"):
        st.write(f"The grouping method compares different numbers of groups. Its separation score is {result.silhouette:.2f} on a scale from -1 to 1; higher means the groups are more distinct. Fields used: {', '.join(result.features_used)}.")

    cols = st.columns(len(result.profiles))
    for col, profile in zip(cols, result.profiles):
        with col:
            st.metric(profile.label, f"{profile.n_transactions} txns", f"{profile.revenue_share_pct:.0f}% of revenue")

    st.divider()
    feature_df = build_segmentation_features(df_filtered)
    st.plotly_chart(
        segmentation_scatter(feature_df, result.labels, x="Total", y="Quantity"),
        use_container_width=True,
    )

    st.subheader("Segment profiles & recommendations")
    for profile in result.profiles:
        with st.expander(f"{profile.label} — {profile.n_transactions} transactions ({profile.share_of_transactions_pct:.0f}%)"):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Avg transaction value", format_currency(profile.avg_total))
            m2.metric("Avg quantity", f"{profile.avg_quantity:.1f}")
            m3.metric("Avg item price", format_currency(profile.avg_item_price))
            m4.metric("Revenue share", format_percent(profile.revenue_share_pct))
            if profile.avg_rating is not None:
                st.caption(f"Average rating: {profile.avg_rating:.1f} / 10")
            st.markdown(f"**Potential action:** {profile.recommendation}")
