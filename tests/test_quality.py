import pandas as pd

from vaultdata.data.quality import assess_quality


def test_clean_data_scores_100():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=5),
            "Total": [10.0, 20.0, 30.0, 40.0, 50.0],
            "Quantity": [1, 2, 3, 4, 5],
            "Product line": ["A", "B", "A", "B", "A"],
        }
    )
    report = assess_quality(df)
    assert report.score == 100
    assert report.n_duplicate_rows == 0
    assert report.n_missing_cells == 0
    assert not report.issues


def test_detects_duplicates_and_missing():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]),
            "Total": [10.0, 10.0, None],
            "Quantity": [1, 1, 2],
            "Product line": ["A", "A", "B"],
        }
    )
    report = assess_quality(df)
    assert report.n_duplicate_rows >= 1
    assert report.n_missing_cells >= 1
    assert report.score < 100


def test_detects_negative_sales_and_impossible_quantity():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=3),
            "Total": [10.0, -5.0, 15.0],
            "Quantity": [1, 0, -2],
            "Product line": ["A", "A", "A"],
        }
    )
    report = assess_quality(df)
    labels = {i.label for i in report.issues}
    assert "Negative sales values" in labels
    assert "Zero/negative quantities" in labels


def test_date_coverage_computed():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=10),
            "Total": range(10),
            "Quantity": range(10),
            "Product line": ["A"] * 10,
        }
    )
    report = assess_quality(df)
    assert report.date_coverage_days == 10
