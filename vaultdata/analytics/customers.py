"""Customer intelligence via transaction-level segmentation.

IMPORTANT, and disclosed in the app itself (see views/about.py): this
dataset has no persistent customer identifier -- every row is a distinct
Invoice ID, and there is no way to link two transactions to the same
shopper. Classic RFM (recency/frequency by an identified customer) is
therefore not computable, and this module does not attempt to fake it.
What it does instead is a legitimate, honestly-scoped alternative: it
segments individual *transactions* by spend, basket size, and satisfaction,
which is a real and useful signal (e.g. for merchandising and promotions)
even though it can't be tied to a repeat shopper over time.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from vaultdata.config import SEGMENTATION_K_RANGE

CANDIDATE_FEATURES = ["Total", "Quantity", "Avg Item Price", "Rating"]

SEGMENT_RECOMMENDATIONS = {
    "High-Value Baskets": (
        "This segment contributes a disproportionate share of revenue per visit. "
        "Potential action: prioritize service quality and loyalty/retention offers "
        "around these higher-spend visits."
    ),
    "Bulk Purchase Baskets": (
        "These visits combine larger quantities at moderate per-item spend. "
        "Potential action: consider volume-based promotions or bundle offers "
        "that reward larger baskets."
    ),
    "Low-Spend / Occasional Baskets": (
        "Lower spend per visit than the overall average. "
        "Potential action: consider entry-level promotions or cross-sell "
        "prompts to grow basket size."
    ),
    "Standard Baskets": (
        "Spend and basket size close to the overall average -- the typical "
        "transaction profile. Potential action: use as the baseline when "
        "measuring the effect of promotions targeted at other segments."
    ),
}


@dataclass
class SegmentProfile:
    label: str
    cluster_id: int
    n_transactions: int
    share_of_transactions_pct: float
    revenue_share_pct: float
    avg_total: float
    avg_quantity: float
    avg_item_price: float
    avg_rating: float | None
    recommendation: str


@dataclass
class SegmentationResult:
    k: int
    silhouette: float
    features_used: list[str]
    labels: np.ndarray
    profiles: list[SegmentProfile] = field(default_factory=list)


def build_segmentation_features(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    features["Total"] = df["Total"]
    features["Quantity"] = df["Quantity"]
    with np.errstate(divide="ignore", invalid="ignore"):
        features["Avg Item Price"] = np.where(df["Quantity"] > 0, df["Total"] / df["Quantity"], np.nan)
    if "Rating" in df.columns:
        features["Rating"] = df["Rating"]
    return features.dropna()


def _label_segment(avg_total: float, avg_quantity: float, overall_avg_total: float, overall_avg_quantity: float) -> str:
    """Derives a human-readable label from the cluster's own computed
    statistics relative to the overall dataset -- never an arbitrary name."""
    total_ratio = avg_total / overall_avg_total if overall_avg_total else 1.0
    qty_ratio = avg_quantity / overall_avg_quantity if overall_avg_quantity else 1.0

    if total_ratio >= 1.25:
        return "High-Value Baskets"
    if total_ratio <= 0.75:
        return "Low-Spend / Occasional Baskets"
    if qty_ratio >= 1.15:
        return "Bulk Purchase Baskets"
    return "Standard Baskets"


def find_best_k(scaled_features: np.ndarray, k_range=SEGMENTATION_K_RANGE) -> tuple[int, float]:
    """Picks the k (within k_range) with the highest silhouette score --
    a real diagnostic, not a fixed k=3 chosen without checking."""
    best_k, best_score = None, -1.0
    for k in k_range:
        if k >= len(scaled_features):
            continue
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(scaled_features)
        score = silhouette_score(scaled_features, labels)
        if score > best_score:
            best_k, best_score = k, score
    return best_k or 2, best_score


def segment_transactions(df: pd.DataFrame, k: int | None = None) -> SegmentationResult | None:
    """Segments transactions in `df`. Returns None if there isn't enough
    usable data to cluster meaningfully (rather than fitting a degenerate
    model on too few rows)."""
    feature_df = build_segmentation_features(df)
    if len(feature_df) < 10:
        return None

    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_df)

    if k is None:
        k, silhouette = find_best_k(scaled)
    else:
        k = max(2, min(k, len(scaled) - 1))
        labels_tmp = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(scaled)
        silhouette = silhouette_score(scaled, labels_tmp)

    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = model.fit_predict(scaled)

    working = feature_df.copy()
    working["Cluster"] = labels
    overall_avg_total = working["Total"].mean()
    overall_avg_quantity = working["Quantity"].mean()
    total_transactions = len(working)
    total_revenue = working["Total"].sum()

    profiles: list[SegmentProfile] = []
    for cluster_id, group in working.groupby("Cluster"):
        avg_total = float(group["Total"].mean())
        avg_quantity = float(group["Quantity"].mean())
        label = _label_segment(avg_total, avg_quantity, overall_avg_total, overall_avg_quantity)
        profiles.append(
            SegmentProfile(
                label=label,
                cluster_id=int(cluster_id),
                n_transactions=len(group),
                share_of_transactions_pct=100 * len(group) / total_transactions,
                revenue_share_pct=100 * group["Total"].sum() / total_revenue if total_revenue else 0.0,
                avg_total=avg_total,
                avg_quantity=avg_quantity,
                avg_item_price=float(group["Avg Item Price"].mean()),
                avg_rating=float(group["Rating"].mean()) if "Rating" in group.columns else None,
                recommendation=SEGMENT_RECOMMENDATIONS[label],
            )
        )
    profiles.sort(key=lambda p: p.avg_total, reverse=True)

    return SegmentationResult(
        k=k,
        silhouette=float(silhouette),
        features_used=list(feature_df.columns),
        labels=labels,
        profiles=profiles,
    )
