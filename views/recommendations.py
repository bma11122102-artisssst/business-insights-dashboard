from __future__ import annotations

import pandas as pd
import streamlit as st
from vaultdata.data.track4 import is_track4
from views.track4 import recommendations

from vaultdata.analytics.customers import segment_transactions
from vaultdata.analytics.inventory import demand_outlook
from vaultdata.analytics.recommendations import generate_recommendations
from vaultdata.analytics.sales import compute_kpis, product_performance


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    if is_track4(df_all):
        recommendations(df_filtered, df_all)
        return
    st.header("Recommendations")
    st.caption("Management actions generated from the current data selection's actual calculated results.")

    if df_filtered.empty:
        st.warning("No transactions match the current filters. Adjust the filters in the sidebar.")
        return

    kpis = compute_kpis(df_filtered, full_df=df_all)
    perf = product_performance(df_filtered)
    segmentation = segment_transactions(df_filtered) if len(df_filtered) >= 10 else None
    outlook = demand_outlook(df_filtered, horizon_days=14)

    recs = generate_recommendations(kpis, perf, segmentation, outlook)

    if not recs:
        st.info("No significant concentration, segment, or demand-trend flags in the current selection.")
        return

    for category in sorted({r.category for r in recs}):
        st.subheader(category)
        for rec in [r for r in recs if r.category == category]:
            with st.container(border=True):
                st.markdown(f"**{rec.finding}**")
                st.write(rec.action)
