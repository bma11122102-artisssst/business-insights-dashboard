import io

import pandas as pd
import pytest

from vaultdata.data.loader import DataLoadError, load_uploaded_dataset, resolve_columns


def test_demo_dataset_loads_and_enriches(demo_df):
    assert len(demo_df) > 0
    for col in ["Date", "Total", "Quantity", "Product line", "Year", "Month", "Weekday", "Sentiment"]:
        assert col in demo_df.columns
    assert demo_df["Date"].dtype.kind == "M"


def test_resolve_columns_maps_aliases():
    df = pd.DataFrame({"sales": [1, 2], "order_date": ["2024-01-01", "2024-01-02"], "qty": [1, 2], "category": ["A", "B"]})
    renamed, result = resolve_columns(df)
    assert "Total" in renamed.columns
    assert "Date" in renamed.columns
    assert "Quantity" in renamed.columns
    assert "Product line" in renamed.columns
    assert result.unmatched_required == []


def test_resolve_columns_reports_missing_required():
    df = pd.DataFrame({"foo": [1, 2]})
    _, result = resolve_columns(df)
    assert set(result.unmatched_required) == {"Date", "Total", "Quantity", "Product line"}


def test_load_uploaded_dataset_rejects_missing_columns():
    csv = "foo,bar\n1,2\n"
    with pytest.raises(DataLoadError, match="missing required column"):
        load_uploaded_dataset(io.StringIO(csv))


def test_load_uploaded_dataset_rejects_empty_file():
    with pytest.raises(DataLoadError):
        load_uploaded_dataset(io.StringIO(""))


def test_load_uploaded_dataset_accepts_aliased_headers():
    csv = "order_date,revenue,units,category\n2024-01-01,100.0,2,Widgets\n2024-01-02,150.0,3,Widgets\n"
    df = load_uploaded_dataset(io.StringIO(csv))
    assert df["Total"].sum() == 250.0
    assert "Weekday" in df.columns
