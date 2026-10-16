from __future__ import annotations

import pandas as pd
import streamlit as st

from vaultdata.analytics.forecasting import METHOD_LABEL, ForecastError, forecast_future
from vaultdata.viz.charts import forecast_chart
from vaultdata.viz.formatting import format_currency
from vaultdata.data.track4 import is_track4, completed
from vaultdata.components.filters import FILTER_STATE_KEY
from views import unit_forecast


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    st.header("Sales forecast")
    st.caption("An estimate of future daily revenue based on past sales patterns.")
    if is_track4(df_all):
        measure=st.radio('What would you like to estimate?',['Sales revenue (₹)','Items sold'],horizontal=True)
        if measure=='Items sold':
            unit_forecast.render(df_filtered)
            return
    bounds = None
    if is_track4(df_all):
        st.caption("Forecasting completed revenue only, after transaction discounts. Cancelled, returned, and pending orders are excluded.")
        df_filtered = completed(df_filtered)
        state = st.session_state.get(FILTER_STATE_KEY)
        bounds = state.date_range if state else None

    if df_filtered.empty:
        st.warning("No transactions match the current filters. Adjust the filters in the sidebar.")
        return

    horizon = st.select_slider("How many days ahead?", options=[7, 14, 30, 60], value=14)
    st.caption(
        "The farther ahead we estimate, the less certain the result. The shaded area shows "
        "a range of possible outcomes, not a guarantee."
    )

    daily_revenue = df_filtered.set_index("Date")["Total"].resample("D").sum()
    if bounds:
        daily_revenue = daily_revenue.reindex(pd.date_range(*bounds, freq="D"), fill_value=0)

    try:
        result = forecast_future(daily_revenue, horizon_days=horizon)
    except ForecastError as exc:
        st.error(str(exc))
        return

    st.plotly_chart(
        forecast_chart(result.history, result.forecast, result.lower, result.upper, f"{horizon}-day revenue forecast"),
        use_container_width=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Forecast total, next {horizon}d", format_currency(result.forecast.sum()))
    c2.metric("Forecast daily average", format_currency(result.forecast.mean()))
    c3.metric("Historical daily average", format_currency(result.history.mean()))

    st.divider()
    st.subheader("How close were past estimates?")
    if result.validation is None:
        st.info("There are not enough past sales in this selection to check forecast accuracy.")
    else:
        v = result.validation
        st.caption(
            f"We kept the latest {v.holdout_days} days out of training, predicted their sales, "
            f"and compared those estimates with what actually happened. Lower errors are better."
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Average daily error", format_currency(v.mae))
        m2.metric("Error with larger misses weighted more", format_currency(v.rmse))
        m3.metric("Average percentage error", f"{v.mape:.1f}%" if v.mape is not None else "N/A")
    with st.expander("How the forecast is calculated"):
        st.write(f"Method: {METHOD_LABEL}. The shaded band is an 80% prediction range calculated from the fitted model. Accuracy is checked using MAE (average absolute error), RMSE (larger errors count more), and MAPE (average percentage error).")
