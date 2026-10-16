# Judging evidence: Track 4

Verified against the [official 100-mark rubric](https://datathon-xi.vercel.app/judging.html) on 16 October 2026. These weights describe the rubric, **not a predicted or awarded score**. All paths are relative to the repository root.

| Criterion | Marks | Inspectable evidence |
|---|---:|---|
| Problem understanding & user need | 10 | Retail/category manager needs to identify affected order value, check stock, and choose next actions. README workflow; `docs/TRACK4_ALIGNMENT.md`; Overview → Sales → Recommendations. |
| Provided dataset usage | 10 | All five original files, 27,450 rows. Validated many-to-one joins, audit and source hashes, per-file roles in `docs/DATA_DICTIONARY.md`. Campaign context is aggregated without invented order attribution. |
| Data Science / ML quality | 15 | `vaultdata/ml/`: temporal splits, purged future labels, train-only preprocessing, validation selection, simple baselines, final test metrics. `reports/evaluation.json` and prediction CSVs make results inspectable. |
| ML model from scratch | 25 | Logistic regression, gradient boosting, Poisson regression, KMeans and IsolationForest are fitted locally on supplied records; no pretrained weights. Forecast methods are fitted on supplied daily histories. `python -m vaultdata.ml.evaluate --output reports` reruns training. No hosted model is used. |
| Working product & workflow | 20 | Streamlit navigation, shared filters, CSV exports, guarded restock scenarios, selectable revenue/items forecast, Model checks. Recommendations supports assigned owner, step completion, review notes and JSON export. Progress is session-only and scoped to supporting evidence. Automated UI/behavior tests live in `tests/`. |
| USP & innovation | 10 | Evidence → action → measurable review: cross-file contradictions are surfaced before ordering; unreliable stock records block quantities; model claims fall back to baselines when appropriate; offline guidance remains available without credentials. These are product differentiators, not claims of a novel algorithm. |
| Impact, feasibility & responsible use | 5 | `docs/ASSUMPTIONS.md` and model cards explain synthetic prices/costs, missing attribution, forecast coverage, noncausal flags and unavailable savings claims. No customer-level punitive decisions. Offline workflow has no service dependency. |
| Demo & presentation | 5 | `docs/DEMO.md`: reproducible walkthrough, expected observations, limits, and commands. README links measured results and source-level evidence. |

## Distinguish training from winning a baseline comparison

Models are trained from scratch using standard libraries; this does not mean implementing learning algorithms manually. Order/stock training is implemented, but validation retained prior-rate baselines. Individual ranking is therefore explicitly unsupported. The campaign diagnostic, unit forecasts and revenue forecast have measured lower held-out errors than their stated baselines; see the generated report for exact scores and dates. These results do not imply the judges will award full marks.

## Independent review

1. Install the tested environment with `python -m pip install -r requirements-lock.txt`.
2. Run `python -m pytest -q`.
3. Run `python -m vaultdata.ml.evaluate --output artifacts/review`.
4. Inspect `artifacts/review/EVALUATION.md`, JSON feature/split metadata and prediction CSVs; compare source hashes with the included files.
5. Run `python -m streamlit run streamlit_app.py` and follow the demo.

The GitHub Actions workflow repeats tests and evaluation and uploads its outputs. A workflow file is not evidence of a successful remote run; inspect the actual Actions result after pushing the submission.

## Round 2 repository requirements

The official Round 2 page specifies no live demo: screenshots and sample outputs are embedded or linked in README. `train.py` provides the training entry point; `docs/ROUND2_SUBMISSION.md` contains the form answers and complete current data/model-service declaration. The additional UCI dataset is explicitly attributed and evaluated as a separate benchmark, not pooled with official data.
