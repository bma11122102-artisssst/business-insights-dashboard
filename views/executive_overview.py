from __future__ import annotations

import pandas as pd
import streamlit as st
from dataclasses import replace
from vaultdata.components.filters import FILTER_STATE_KEY, apply_filters

from vaultdata.analytics.sales import compute_kpis, product_performance
from vaultdata.components.kpis import render_kpi_row
from vaultdata.viz.charts import ranking_bar_chart, revenue_trend_chart
from vaultdata.data.track4 import is_track4, completed
from views.track4 import overview_additions
from views.track4 import supporting_data
from vaultdata.viz.formatting import format_currency


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    st.header("Overview")
    st.caption("See how the business is doing with your selected filters.")
    if is_track4(df_all):
        done = completed(df_filtered)
        stock, campaigns = supporting_data()
        state = st.session_state.get(FILTER_STATE_KEY)
        prior = apply_filters(completed(df_all),replace(state,date_range=None)) if state else completed(df_all)
        kpis = compute_kpis(done,full_df=prior)
        if len(df_filtered):
            st.caption(f"{df_filtered.Date.min():%d %b %Y} – {df_filtered.Date.max():%d %b %Y} · {len(df_filtered):,} total orders · Money shown in ₹")
        first = st.columns(4)
        first[0].metric('Sales revenue',format_currency(kpis.total_revenue,decimals=0),delta=f'{kpis.revenue_growth_pct:+.1f}%' if kpis.revenue_growth_pct is not None else None,help='Sales after discounts, from completed orders only. A change is shown only when a full earlier period is available with the same filters.')
        first[1].metric('Completed orders',f'{len(done):,}')
        first[2].metric('Items sold',f'{int(done.Quantity.sum()):,}')
        first[3].metric('Average order value',format_currency(kpis.avg_transaction_value))
        second = st.columns(4)
        second[0].metric('Cancelled order value',format_currency(df_filtered.loc[df_filtered.Status=='Cancelled','Total'].sum(),decimals=0))
        second[1].metric('Returned order value',format_currency(df_filtered.loc[df_filtered.Status=='Returned','Total'].sum(),decimals=0))
        second[2].metric('Products needing a stock check',f'{int((stock.Signal!="Healthy").sum()):,}',help='Products reported out of stock or running low. Uses date and category filters only.')
        second[3].metric('Marketing spend',format_currency(campaigns.spend.sum(),decimals=0),help='Uses date, category, and channel filters. Customer filters cannot apply to campaigns.')
        st.caption('Sales count completed orders only. Cancelled and returned values are shown separately; they are not proven losses or promised recoveries. Stock and marketing have fewer filters than orders.')
        left,right = st.columns([1.7,1])
        with left,st.container(border=True):
            if not done.empty:
                daily = done.set_index('Date').Total.resample('D').sum()
                if state and state.date_range:
                    daily=daily.reindex(pd.date_range(*state.date_range,freq='D'),fill_value=0)
                st.plotly_chart(revenue_trend_chart(daily,'Sales revenue over time'),width='stretch')
            else:
                st.info('No completed sales match these filters.')
        with right,st.container(border=True):
            if not done.empty:
                st.plotly_chart(ranking_bar_chart(product_performance(done),'Revenue','Best-selling categories','Revenue (₹)'),width='stretch')
            else:
                st.info('No category sales to show.')
        overview_additions(df_filtered)
        with st.expander('Discounts, product costs, and customer totals'):
            a,b,c,d=st.columns(4)
            a.metric('Discounts on completed orders',format_currency(done['Discount value'].sum(),decimals=0))
            b.metric('Recorded product costs',format_currency(done.cogs.sum(),decimals=0))
            c.metric('Sales minus product costs',format_currency(done['Estimated margin'].sum(),decimals=0))
            d.metric('Customers who bought',f'{done.customer_id.nunique():,}')
            st.caption('Sales minus product costs is not net profit: marketing and other costs are not deducted. The sample costs and prices were created separately, so this is only an illustration. Money is displayed as rupees without an exchange-rate conversion.')
        return
    state = st.session_state.get(FILTER_STATE_KEY)
    if state:
        df_all = apply_filters(df_all, replace(state, date_range=None))

    if df_filtered.empty:
        st.warning("No transactions match the current filters. Adjust the filters in the sidebar.")
        return

    kpis = compute_kpis(df_filtered, full_df=df_all)
    render_kpi_row(kpis)

    st.divider()

    col1, col2 = st.columns([2, 1])
    with col1:
        trend = df_filtered.set_index("Date")["Total"].resample("D").sum()
        st.plotly_chart(revenue_trend_chart(trend, "Daily revenue trend"), use_container_width=True)
    with col2:
        perf = product_performance(df_filtered)
        st.plotly_chart(
            ranking_bar_chart(perf, "Revenue", "Revenue by product line", x_title="Revenue (₹)"),
            use_container_width=True,
        )

    st.caption(
        "All figures reflect the current filter selection only. Revenue growth compares this "
        "selection's date range to the immediately preceding period of equal length, when "
        "sufficient prior data exists."
    )
