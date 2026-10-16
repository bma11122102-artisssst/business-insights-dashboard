# Five-minute self-guided review

Round 2 is repository-only judging with no live demo. This walkthrough helps readers inspect the product; README screenshots provide the visible evidence.

Start: `python -m streamlit run streamlit_app.py`. Choose **Track 4 · The Money Leak**, retain full-year/default filters. No credentials are needed.

1. **User and need (30 sec).** A retail manager has sales, stock and marketing spreadsheets but no clear priority list. LeakLens connects the evidence and turns findings into reviewable next steps.
2. **Overview and Sales (60 sec).** Show completed revenue in ₹, cancellations/returns and category breakdowns. Explain that affected order value is neither recoverable money nor audited loss. Change a category filter and show the figures respond; reset before proceeding.
3. **Data and Stock (60 sec).** Inspect the original five files and consistency warnings. Explain the 760 historical flag/quantity conflicts. The Stock page uses latest selected records, so its conflict count can differ. Build a restock example: stale or contradictory rows block quantity suggestions. This is a planning scenario using recorded sales and lead times.
4. **Forecast and Model checks (90 sec).** Show items forecast, then Model checks. Explain locally fitted candidates, earlier validation, and untouched later test periods. Campaign MAE is about 361 versus 448; all-category unit MAE about 14.7 versus 19.6. Campaign estimation uses already measured clicks, not pre-launch information. Order/stock baselines won: explicitly show their ranking warnings. Do not call clustering separation an accuracy score.
5. **Recommendations (45 sec).** Open the offline checklist, assign an owner, tick a step and record a finding/review note. Download the checklist. Explain that source data remains unchanged, progress lasts only for this session, and changed evidence starts separate progress. Track actual business outcomes after interventions before claiming benefit.
6. **Reproducibility (15 sec).** Open `reports/EVALUATION.md`, `docs/JUDGING_EVIDENCE.md` and the evaluation command in README. All model training and recommendations run locally.

If saved model checks report changed files, rerun evaluation; do not present stale results. No live service, production deployment, confirmed savings or guaranteed rubric score is claimed.
