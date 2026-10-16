"""Business recommendations engine.

Every recommendation here is generated from the actual computed analytics
objects passed in (KPIs, product performance, segmentation, demand outlook)
-- nothing is hardcoded independent of the current data/filters. If a
condition isn't met by the data, that recommendation simply doesn't appear.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from vaultdata.analytics.customers import SegmentationResult
from vaultdata.analytics.inventory import ProductDemandForecast
from vaultdata.analytics.sales import KPISet

REVENUE_CONCENTRATION_SHARE = 40.0  # top-2 product lines' combined revenue share, %
SEGMENT_DISPROPORTIONALITY_POINTS = 10.0  # revenue share minus transaction share, pts


@dataclass
class Recommendation:
    category: str
    finding: str
    action: str
    is_caveat: bool = True


def _caveat(text: str) -> str:
    return f"{text} This is an analytical recommendation based on the current data selection, not a guaranteed outcome."


def generate_recommendations(
    kpis: KPISet,
    product_perf: pd.DataFrame | None,
    segmentation: SegmentationResult | None,
    demand_outlook: list[ProductDemandForecast] | None,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if product_perf is not None and not product_perf.empty:
        top_two_share = product_perf["Revenue Share %"].sort_values(ascending=False).head(2).sum()
        if top_two_share >= REVENUE_CONCENTRATION_SHARE:
            top_lines = ", ".join(product_perf.sort_values("Revenue", ascending=False).head(2).index)
            recs.append(
                Recommendation(
                    category="Revenue",
                    finding=(
                        f"Revenue is concentrated in a small number of product lines -- "
                        f"{top_lines} together account for {top_two_share:.0f}% of revenue "
                        f"in the current selection."
                    ),
                    action=_caveat(
                        "Prioritize inventory availability and promotional activity for these "
                        "highest-performing categories."
                    ),
                )
            )

    if segmentation is not None and segmentation.profiles:
        high_value = next((p for p in segmentation.profiles if p.label == "High-Value Baskets"), None)
        if high_value is not None:
            disproportionality = high_value.revenue_share_pct - high_value.share_of_transactions_pct
            if disproportionality >= SEGMENT_DISPROPORTIONALITY_POINTS:
                recs.append(
                    Recommendation(
                        category="Customers",
                        finding=(
                            f"The High-Value Baskets segment is {high_value.share_of_transactions_pct:.0f}% "
                            f"of transactions but {high_value.revenue_share_pct:.0f}% of revenue in the "
                            f"current selection -- a disproportionate share of spending."
                        ),
                        action=_caveat(
                            "Consider targeted retention initiatives or personalized offers for this segment."
                        ),
                    )
                )

    if demand_outlook:
        stockout = [d.product_line for d in demand_outlook if d.risk == "Potential stockout risk"]
        overstock = [d.product_line for d in demand_outlook if d.risk == "Potential overstock risk"]
        if stockout:
            recs.append(
                Recommendation(
                    category="Inventory",
                    finding=(
                        f"Forecast demand indicates increased demand for: {', '.join(stockout)}."
                    ),
                    action=_caveat("Review procurement and replenishment planning for these product lines."),
                )
            )
        if overstock:
            recs.append(
                Recommendation(
                    category="Inventory",
                    finding=(
                        f"Forecast demand indicates declining demand for: {', '.join(overstock)}."
                    ),
                    action=_caveat("Review order quantities for these product lines to avoid excess stock."),
                )
            )

    if kpis.revenue_growth_pct is not None and abs(kpis.revenue_growth_pct) >= 10:
        direction = "up" if kpis.revenue_growth_pct > 0 else "down"
        recs.append(
            Recommendation(
                category="Revenue",
                finding=f"Revenue is {direction} {abs(kpis.revenue_growth_pct):.0f}% versus the prior period of equal length.",
                action=_caveat(
                    "Investigate the drivers behind this change (product mix, branch, promotions) "
                    "before adjusting plans."
                ),
            )
        )

    return recs
