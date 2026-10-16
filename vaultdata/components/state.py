"""Streamlit-facing dataset loading: caching + upload handling + session
state. This is the thin UI-aware wrapper around the pure vaultdata.data
functions -- kept separate so the loading/validation logic itself stays
unit-testable without a Streamlit runtime.
"""
from __future__ import annotations

import streamlit as st

from vaultdata.data.loader import DataLoadError, load_dataset, load_uploaded_dataset
from vaultdata.data.track4 import load_sources, prepare_transactions

DATASET_SESSION_KEY = "vaultdata_active_dataset_source"  # "demo" or "uploaded"


@st.cache_data(show_spinner="Connecting the five Track 4 datasets...")
def track4_sources():
    return load_sources()


@st.cache_data
def _cached_track4_dataset():
    return prepare_transactions(track4_sources())


@st.cache_data(show_spinner="Loading demo dataset...")
def _cached_default_dataset():
    return load_dataset()


@st.cache_data(show_spinner="Processing uploaded dataset...")
def _cached_uploaded_dataset(file_bytes: bytes, file_name: str):
    import io

    return load_uploaded_dataset(io.BytesIO(file_bytes))


def render_dataset_picker() -> tuple[object, str] | tuple[None, None]:
    """Renders the upload widget (sidebar) and returns (dataframe, source_label).

    Falls back to the bundled demo dataset when nothing is uploaded, and
    shows a clear error (not a traceback) if an uploaded file fails
    validation -- the demo dataset stays available in that case so the app
    never dead-ends.
    """
    st.sidebar.markdown("**Dataset**")
    source = st.sidebar.selectbox("Data source", ["Track 4 · The Money Leak", "Original supermarket demo", "Upload CSV"], key="data_source")
    if source == "Track 4 · The Money Leak":
        try:
            df = _cached_track4_dataset()
            st.sidebar.caption("5 official files · 27,450 source records · synthetic data")
            return df, "Official DATATHON Track 4"
        except DataLoadError as exc:
            st.error(str(exc))
            return None, None
    if source == "Original supermarket demo":
        return _cached_default_dataset(), "Original demo: supermarket_sales.csv"
    uploaded = st.sidebar.file_uploader(
        "Upload your own CSV (optional)",
        type=["csv"],
        help="Needs at minimum a date column, a numeric sales/total column, a quantity "
        "column, and a product/category column. Falls back to the demo dataset if you "
        "don't upload anything.",
    )

    if uploaded is not None:
        try:
            df = _cached_uploaded_dataset(uploaded.getvalue(), uploaded.name)
            st.sidebar.success(f"Using uploaded file: {uploaded.name}")
            return df, f"Uploaded: {uploaded.name}"
        except DataLoadError as exc:
            st.sidebar.error(str(exc))
            st.sidebar.info("Continuing with the demo dataset below.")

    try:
        df = _cached_default_dataset()
    except DataLoadError as exc:
        st.error(str(exc))
        return None, None
    return df, "Demo dataset: supermarket_sales.csv"
