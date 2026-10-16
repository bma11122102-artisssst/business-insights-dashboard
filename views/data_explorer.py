from __future__ import annotations

import pandas as pd
import streamlit as st

from vaultdata.data.quality import assess_quality
from vaultdata.data.track4 import is_track4
from views.track4 import source_explorer
from vaultdata.viz.labels import readable_table
from vaultdata.viz.formatting import MONEY_COLUMNS


def render(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> None:
    st.header("Data")
    st.caption("Search and download your selected orders. Checks for missing or repeated information use the full orders file.")
    if is_track4(df_all):
        source_explorer()

    quality = assess_quality(df_all)

    st.subheader("File checks")
    q1, q2, q3, q4, q5 = st.columns(5)
    q1.metric("Rows", f"{quality.n_rows:,}")
    q2.metric("Columns", quality.n_columns)
    q3.metric("Missing values", f"{quality.n_missing_cells:,}", f"{quality.missing_pct:.1f}%" if quality.n_missing_cells else None)
    q4.metric("Duplicate records", quality.n_duplicate_rows)
    date_coverage = f"{quality.date_coverage_days} days" if quality.date_coverage_days else "N/A"
    q5.metric("Date coverage", date_coverage)

    st.metric("Missing/duplicate/value checks score", f"{quality.score} / 100")
    if is_track4(df_all):
        st.info('This score covers missing values, duplicates, and basic value checks only. It does not certify that dates, stock flags, prices, or campaign counts agree. See the cross-file checks above and Model checks for those issues.')
    st.caption(
        "Score starts at 100 and deducts for duplicate rows, missing cells, and hard data errors "
        "(negative sales, impossible quantities), scaled by how much of the dataset each affects. "
        "It's a readable summary, not a formal statistical index."
    )

    if quality.issues:
        with st.expander(f"{len(quality.issues)} data-quality issue(s) found"):
            for issue in quality.issues:
                icon = {"error": "🔴", "warning": "🟠", "info": "🔵"}[issue.severity]
                st.write(f"{icon} **{issue.label}**: {issue.count}" + (f" — {issue.detail}" if issue.detail else ""))
    else:
        st.success("No missing-value, duplicate, or basic value errors found in the combined orders table.")

    st.divider()
    st.subheader("Orders")
    search = st.text_input("Search across all columns", "")
    view_df = df_filtered
    if search:
        mask = view_df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False, regex=False)).any(axis=1)
        view_df = view_df[mask]

    st.caption(f"Showing {len(view_df):,} of {len(df_filtered):,} filtered rows ({len(df_all):,} total in dataset).")
    display = readable_table(view_df)
    st.dataframe(display, column_config={name:st.column_config.NumberColumn(format='₹%.2f') for name in display.columns if name in MONEY_COLUMNS}, use_container_width=True, height=420)

    st.download_button(
        "Download filtered data (CSV)",
        data=view_df.to_csv(index=False).encode("utf-8"),
        file_name="ntr_filtered_export.csv",
        mime="text/csv",
    )

    with st.expander("Column data types"):
        st.dataframe(pd.DataFrame({"Column": df_all.columns, "Type": df_all.dtypes.astype(str).values}), use_container_width=True, hide_index=True)
