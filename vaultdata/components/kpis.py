"""KPI card rendering."""
from __future__ import annotations

import streamlit as st

from vaultdata.analytics.sales import KPISet
from vaultdata.viz.formatting import format_currency, format_number, format_percent


def render_kpi_row(kpis: KPISet) -> None:
    growth_delta = format_percent(kpis.revenue_growth_pct, signed=True) if kpis.revenue_growth_pct is not None else None

    row1 = st.columns(3)
    row1[0].metric("Total Revenue", format_currency(kpis.total_revenue), delta=growth_delta)
    row1[1].metric("Completed orders", format_number(kpis.total_transactions))
    row1[2].metric("Units Sold", format_number(kpis.units_sold))

    row2 = st.columns(3 if kpis.avg_rating is not None else 2)
    row2[0].metric("Average order value", format_currency(kpis.avg_transaction_value))
    row2[1].metric("Best-selling category by revenue", kpis.top_product_line or "N/A")
    if kpis.avg_rating is not None:
        row2[2].metric("Avg Customer Rating", f"{kpis.avg_rating:.1f} / 10")

    if kpis.revenue_growth_pct is None:
        st.caption(
            "Revenue growth isn't shown when there's no prior period of equal length in the "
            "current selection to compare against."
        )
