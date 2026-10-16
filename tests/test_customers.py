import numpy as np
import pandas as pd
import pytest

from vaultdata.analytics.customers import segment_transactions


def test_segment_transactions_none_when_too_few_rows():
    df = pd.DataFrame({"Total": [10, 20, 30], "Quantity": [1, 2, 3], "Rating": [5, 6, 7]})
    assert segment_transactions(df) is None


def test_segment_transactions_separates_high_and_low_spend():
    rng = np.random.default_rng(0)
    low = pd.DataFrame({"Total": rng.normal(20, 2, 30), "Quantity": rng.integers(1, 3, 30), "Rating": rng.uniform(4, 6, 30)})
    high = pd.DataFrame({"Total": rng.normal(200, 5, 30), "Quantity": rng.integers(3, 6, 30), "Rating": rng.uniform(7, 9, 30)})
    df = pd.concat([low, high], ignore_index=True)

    result = segment_transactions(df, k=2)
    assert result is not None
    assert result.k == 2
    assert -1.0 <= result.silhouette <= 1.0
    assert sum(p.n_transactions for p in result.profiles) == len(df)

    labels = {p.label for p in result.profiles}
    assert "High-Value Baskets" in labels

    total_share = sum(p.revenue_share_pct for p in result.profiles)
    assert total_share == pytest.approx(100.0)


def test_segment_profiles_have_recommendations():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"Total": rng.normal(50, 15, 40), "Quantity": rng.integers(1, 8, 40), "Rating": rng.uniform(4, 9, 40)})
    result = segment_transactions(df, k=3)
    assert result is not None
    for profile in result.profiles:
        assert profile.recommendation
        assert profile.n_transactions > 0
