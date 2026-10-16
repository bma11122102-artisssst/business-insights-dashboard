"""VaultData Business Intelligence Dashboard -- entrypoint.

Loads the dataset and renders the shared sidebar (dataset picker + filters)
once per run, then delegates to the selected page via st.navigation -- the
current Streamlit-recommended multipage pattern. Code above
`st.navigation(...).run()` executes on every page view, which is where the
shared dataset/filter state is set up.
"""
from __future__ import annotations

import streamlit as st

from vaultdata.components.filters import apply_filters, render_filters
from vaultdata.components.state import render_dataset_picker
from vaultdata.config import APP_STATUS, APP_TAGLINE, APP_TITLE, BRAND_LINE, LOGO_PATH
from vaultdata.components.theme import apply_theme
from views import (
    about,
    customer_intelligence,
    data_explorer,
    executive_overview,
    forecasting,
    inventory_intelligence,
    recommendations,
    sales_intelligence,
    campaign_intelligence,
    model_checks,
)

st.set_page_config(page_title=APP_TITLE, page_icon=None, layout="wide")
apply_theme()

st.image(str(LOGO_PATH), width=360)
st.caption(APP_TITLE)
st.caption(f"{APP_TAGLINE}  ·  {APP_STATUS}")

df_all, source_label = render_dataset_picker()
if df_all is None:
    st.stop()

filter_state = render_filters(df_all)
df_filtered = apply_filters(df_all, filter_state)

st.sidebar.markdown("---")
st.sidebar.caption(f"Source: {source_label}")
st.sidebar.caption(f"{len(df_filtered):,} of {len(df_all):,} rows in current selection")
st.sidebar.markdown("---")
st.sidebar.caption(BRAND_LINE)
st.sidebar.caption("Money is shown in ₹. Sample amounts are not exchange-rate converted.")


def _executive_overview():
    executive_overview.render(df_filtered, df_all)


def _sales_intelligence():
    sales_intelligence.render(df_filtered, df_all)


def _customer_intelligence():
    customer_intelligence.render(df_filtered, df_all)


def _inventory_intelligence():
    inventory_intelligence.render(df_filtered, df_all)


def _forecasting():
    forecasting.render(df_filtered, df_all)


def _recommendations():
    recommendations.render(df_filtered, df_all)


def _data_explorer():
    data_explorer.render(df_filtered, df_all)


def _about():
    about.render(df_filtered, df_all)


def _campaigns():
    campaign_intelligence.render(df_filtered, df_all)


def _model_checks():
    model_checks.render(df_filtered,df_all)


pages = [
    st.Page(_executive_overview, title="Overview", default=True),
    st.Page(_sales_intelligence, title="Sales"),
    st.Page(_customer_intelligence, title="Customers"),
    st.Page(_inventory_intelligence, title="Stock"),
    st.Page(_campaigns, title="Marketing"),
    st.Page(_forecasting, title="Sales forecast"),
    st.Page(_recommendations, title="Recommendations"),
    st.Page(_model_checks, title="Model checks"),
    st.Page(_data_explorer, title="Data"),
    st.Page(_about, title="How it works"),
]

st.navigation(pages).run()
