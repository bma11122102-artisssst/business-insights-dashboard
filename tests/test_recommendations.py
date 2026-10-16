import pandas as pd

from vaultdata.analytics.customers import SegmentationResult, SegmentProfile
from vaultdata.analytics.inventory import ProductDemandForecast
from vaultdata.analytics.recommendations import generate_recommendations
from vaultdata.analytics.sales import KPISet


def _kpis(**overrides):
    base = dict(
        total_revenue=1000.0,
        total_transactions=20,
        units_sold=50,
        avg_transaction_value=50.0,
        top_product_line="Widgets",
        top_product_line_revenue=500.0,
        avg_rating=7.0,
        revenue_growth_pct=None,
    )
    base.update(overrides)
    return KPISet(**base)


def test_no_recommendations_when_nothing_triggers():
    # 6 evenly-split product lines -- top two only sum to ~33%, below the
    # 40% concentration threshold, so no revenue-concentration recommendation.
    perf = pd.DataFrame(
        {"Revenue": [100] * 6, "Revenue Share %": [16.7] * 6},
        index=["A", "B", "C", "D", "E", "F"],
    )
    recs = generate_recommendations(_kpis(), perf, None, [])
    assert recs == []


def test_revenue_concentration_flagged():
    perf = pd.DataFrame(
        {"Revenue": [800, 100, 100], "Revenue Share %": [80.0, 10.0, 10.0]},
        index=["Widgets", "Gadgets", "Sprockets"],
    )
    recs = generate_recommendations(_kpis(), perf, None, [])
    assert any(r.category == "Revenue" and "concentrated" in r.finding for r in recs)


def test_high_value_segment_disproportionate_share_flagged():
    profile = SegmentProfile(
        label="High-Value Baskets",
        cluster_id=0,
        n_transactions=10,
        share_of_transactions_pct=20.0,
        revenue_share_pct=60.0,
        avg_total=200.0,
        avg_quantity=5.0,
        avg_item_price=40.0,
        avg_rating=8.0,
        recommendation="x",
    )
    segmentation = SegmentationResult(k=2, silhouette=0.4, features_used=["Total"], labels=[0], profiles=[profile])
    recs = generate_recommendations(_kpis(), None, segmentation, [])
    assert any(r.category == "Customers" for r in recs)


def test_inventory_stockout_and_overstock_flagged():
    outlook = [
        ProductDemandForecast("Widgets", 100, 5.0, 8.0, 112.0, "Increasing", "Potential stockout risk", "act"),
        ProductDemandForecast("Gadgets", 100, 5.0, 2.0, 28.0, "Decreasing", "Potential overstock risk", "act"),
    ]
    recs = generate_recommendations(_kpis(), None, None, outlook)
    categories_findings = [(r.category, r.finding) for r in recs]
    assert any("Widgets" in f for _, f in categories_findings)
    assert any("Gadgets" in f for _, f in categories_findings)


def test_revenue_growth_flagged_when_large():
    recs = generate_recommendations(_kpis(revenue_growth_pct=25.0), None, None, [])
    assert any(r.category == "Revenue" and "up 25" in r.finding for r in recs)


def test_small_revenue_growth_not_flagged():
    recs = generate_recommendations(_kpis(revenue_growth_pct=2.0), None, None, [])
    assert recs == []
