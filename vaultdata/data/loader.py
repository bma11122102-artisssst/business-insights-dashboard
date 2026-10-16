"""Dataset loading, column mapping, and validation.

Deliberately has no Streamlit import -- this module is pure pandas so it can
be unit-tested directly and reused outside the app if needed. UI-facing
concerns (file upload widgets, caching, st.error) live in
vaultdata/components/state.py, which calls into this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from vaultdata.config import COLUMN_ALIASES, DEFAULT_DATASET_PATH, REQUIRED_COLUMNS


class DataLoadError(Exception):
    """Raised when a dataset can't be loaded/validated -- message is written
    to be shown to a user directly, not just logged."""


@dataclass
class ColumnMappingResult:
    renamed: dict[str, str] = field(default_factory=dict)
    unmatched_required: list[str] = field(default_factory=list)


def resolve_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, ColumnMappingResult]:
    """Renames whatever headers `df` has to the app's canonical column names
    using vaultdata.config.COLUMN_ALIASES (case/whitespace-insensitive), so a
    real-world export that calls the same field "sales" instead of "Total"
    still works without the user renaming anything by hand.
    """
    lookup: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        lookup[canonical.strip().lower()] = canonical
        for alias in aliases:
            lookup[alias.strip().lower()] = canonical

    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in lookup:
            rename_map[col] = lookup[key]

    renamed_df = df.rename(columns=rename_map)
    present = set(renamed_df.columns)
    missing_required = [c for c in REQUIRED_COLUMNS if c not in present]
    return renamed_df, ColumnMappingResult(renamed=rename_map, unmatched_required=missing_required)


def _parse_date_column(df: pd.DataFrame) -> pd.DataFrame:
    parsed = pd.to_datetime(df["Date"], errors="coerce")
    n_invalid = int(parsed.isna().sum() - df["Date"].isna().sum())
    if n_invalid > 0:
        df = df.loc[parsed.notna()].copy()
        parsed = parsed.loc[parsed.notna()]
    df["Date"] = parsed
    return df


def _parse_time_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Time" not in df.columns:
        return df
    parsed = pd.to_datetime(df["Time"].astype(str), errors="coerce", format="mixed")
    df["Hour"] = parsed.dt.hour
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Adds derived columns the analytics layer depends on. Every addition
    here is either a straightforward date-part extraction or a clearly
    documented, explainable rule (Sentiment) -- nothing here fabricates data.
    """
    df = df.copy()
    df = _parse_date_column(df)
    df = _parse_time_column(df)

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Weekday"] = df["Date"].dt.day_name()
    df["WeekdayNum"] = df["Date"].dt.weekday

    if "Rating" in df.columns:
        # Documented, fixed thresholds on the dataset's own 1-10 rating
        # scale -- not a model, just a readable bucketing shown as such
        # wherever Sentiment appears (see views/about.py methodology text).
        df["Sentiment"] = np.select(
            [df["Rating"] >= 7, df["Rating"] >= 4],
            ["Positive", "Neutral"],
            default="Negative",
        )

    return df


def load_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> pd.DataFrame:
    """Loads and validates the bundled demo dataset (or any CSV path)."""
    try:
        raw = pd.read_csv(path)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Dataset not found at {path}.") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DataLoadError(f"Could not parse {path} as CSV: {exc}") from exc
    return _prepare(raw)


def load_uploaded_dataset(file_obj) -> pd.DataFrame:
    """Loads a user-uploaded CSV (a Streamlit UploadedFile or any
    file-like/path object pandas.read_csv accepts). Raises DataLoadError
    with a message safe to show directly in the UI on any failure."""
    try:
        raw = pd.read_csv(file_obj)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise DataLoadError(f"Could not read this file as CSV: {exc}") from exc
    if raw.empty:
        raise DataLoadError("The uploaded file has no rows.")
    return _prepare(raw)


def _prepare(raw: pd.DataFrame) -> pd.DataFrame:
    mapped, mapping_result = resolve_columns(raw)
    if mapping_result.unmatched_required:
        missing = ", ".join(mapping_result.unmatched_required)
        raise DataLoadError(
            f"This file is missing required column(s): {missing}. "
            f"Forecasting and analytics need a date column, a numeric sales/total "
            f"measure, a quantity measure, and a product/category column."
        )
    try:
        return enrich(mapped)
    except (KeyError, ValueError, TypeError) as exc:
        raise DataLoadError(f"Could not process this dataset: {exc}") from exc
