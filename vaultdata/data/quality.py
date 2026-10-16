"""Automated data-quality checks.

Every check here is a plain, explainable rule -- no ML, no silent
mutation. `assess_quality` never modifies the input; it only reports.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class QualityIssue:
    label: str
    count: int
    severity: str  # "info" | "warning" | "error"
    detail: str = ""


@dataclass
class QualityReport:
    n_rows: int
    n_columns: int
    n_missing_cells: int
    missing_by_column: dict[str, int]
    n_duplicate_rows: int
    date_min: pd.Timestamp | None
    date_max: pd.Timestamp | None
    date_coverage_days: int | None
    issues: list[QualityIssue] = field(default_factory=list)
    score: int = 100

    @property
    def missing_pct(self) -> float:
        total_cells = self.n_rows * self.n_columns
        return 0.0 if total_cells == 0 else round(100 * self.n_missing_cells / total_cells, 2)


def assess_quality(df: pd.DataFrame) -> QualityReport:
    n_rows, n_columns = df.shape
    missing_by_column = {c: int(n) for c, n in df.isna().sum().items() if n > 0}
    n_missing_cells = int(df.isna().sum().sum())
    n_duplicate_rows = int(df.duplicated().sum())

    date_min = date_max = None
    date_coverage_days = None
    if "Date" in df.columns and df["Date"].notna().any():
        date_min = df["Date"].min()
        date_max = df["Date"].max()
        date_coverage_days = int((date_max - date_min).days) + 1

    issues: list[QualityIssue] = []

    if n_duplicate_rows:
        issues.append(QualityIssue("Duplicate rows", n_duplicate_rows, "warning"))

    if missing_by_column:
        issues.append(
            QualityIssue(
                "Columns with missing values",
                len(missing_by_column),
                "warning",
                detail=", ".join(f"{c} ({n})" for c, n in missing_by_column.items()),
            )
        )

    if "Total" in df.columns:
        n_negative_sales = int((df["Total"] < 0).sum())
        if n_negative_sales:
            issues.append(QualityIssue("Negative sales values", n_negative_sales, "error"))

    if "Quantity" in df.columns:
        n_impossible_qty = int((df["Quantity"] <= 0).sum())
        if n_impossible_qty:
            issues.append(QualityIssue("Zero/negative quantities", n_impossible_qty, "error"))

    for cat_col in ("Product line", "Branch", "Customer type", "Payment"):
        if cat_col in df.columns:
            n_blank = int(df[cat_col].isna().sum() + (df[cat_col].astype(str).str.strip() == "").sum())
            if n_blank:
                issues.append(QualityIssue(f"Missing '{cat_col}' values", n_blank, "warning"))

    if "Total" in df.columns and n_rows >= 10:
        q1, q3 = df["Total"].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_outliers = int(((df["Total"] < lower) | (df["Total"] > upper)).sum())
        if n_outliers:
            issues.append(
                QualityIssue(
                    "Transaction-value outliers (IQR method)",
                    n_outliers,
                    "info",
                    detail=f"Outside [{lower:,.2f}, {upper:,.2f}]",
                )
            )

    # Simple, documented deduction score -- not a statistical index, just a
    # readable summary: start at 100, deduct for each category of problem
    # scaled by how much of the dataset it touches, floor at 0.
    score = 100.0
    if n_rows:
        score -= min(30, 100 * n_duplicate_rows / n_rows)
        score -= min(30, 100 * n_missing_cells / (n_rows * max(n_columns, 1)))
        for issue in issues:
            if issue.severity == "error":
                score -= min(20, 100 * issue.count / n_rows)
    score = round(max(0.0, min(100.0, score)))

    return QualityReport(
        n_rows=n_rows,
        n_columns=n_columns,
        n_missing_cells=n_missing_cells,
        missing_by_column=missing_by_column,
        n_duplicate_rows=n_duplicate_rows,
        date_min=date_min,
        date_max=date_max,
        date_coverage_days=date_coverage_days,
        issues=issues,
        score=int(score),
    )
