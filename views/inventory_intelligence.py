from __future__ import annotations

import pandas as pd
import streamlit as st
from vaultdata.data.track4 import is_track4
from views.track4 import inventory

from vaultdata.analytics.inventory import demand_outlook
from vaultdata.viz.charts import demand_outlook_chart

RISK_ICON = {
    "Potential stockout risk": "🔺",
    "Potential overstock risk": "🔻",
    "Balanced demand outlook": "▪️",
}


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    if is_track4(df_all):
        inventory(df_filtered, df_all)
        return
    st.header("Stock")
    st.warning(
        "This file contains sales, but no stock records. The estimates below show whether "
        "product sales are rising or falling. They cannot tell us which products are actually "
        "out of stock. Choose the Track 4 files to see recorded stock levels.",
        icon="⚠️",
    )

    if df_filtered.empty:
        st.warning("No transactions match the current filters. Adjust the filters in the sidebar.")
        return

    horizon = st.select_slider("How many days ahead?", options=[7, 14, 30, 60], value=14)
    outlook = demand_outlook(df_filtered, horizon_days=horizon)
    if not outlook:
        st.info("Not enough data to produce a demand outlook for the current selection.")
        return

    chart_rows = [
        {
            "Product line": o.product_line,
            "Observed avg daily demand": o.observed_avg_daily_demand,
            "Forecast avg daily demand": o.forecast_daily_demand,
        }
        for o in outlook
    ]
    st.plotly_chart(demand_outlook_chart(chart_rows, f"Demand outlook — next {horizon} days"), use_container_width=True)

    st.subheader("Demand outlook by product line")
    table = pd.DataFrame(
        [
            {
                "Product": o.product_line,
                "Observed avg daily demand": f"{o.observed_avg_daily_demand:.1f} units/day",
                f"Forecast demand ({horizon}d)": f"{o.forecast_horizon_units:.0f} units",
                "Trend": o.trend_direction,
                "Risk indicator": f"{RISK_ICON[o.risk]} {o.risk}",
                "Suggested action": o.suggested_action,
            }
            for o in outlook
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)
