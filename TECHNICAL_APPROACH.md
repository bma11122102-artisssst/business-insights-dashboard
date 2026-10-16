# LeakLens — Technical Approach

LeakLens extends NTR's original Streamlit dashboard for DATATHON Track 4, The Money Leak. It connects all five official business datasets and turns supporting numbers into a practical investigation and action plan.

## Data foundation

The system loads 27,450 customer, product, order, stock, and campaign records. Contracts check columns, identifiers, references, ranges, and dates. Validated customer/product joins enrich orders; product joins enrich stock. Campaign context is combined only after both sales and campaign records are aggregated to unique date/category/channel keys. It never attributes an individual order to a campaign.

The audit preserves raw files while identifying signup/order date conflicts, stock flags that disagree with quantities, impossible campaign counts, repeated product/date observations, and independently generated cost-price inconsistencies. Each model documents exclusions and feature timing.

## Models and measured checks

- **Order outcomes:** Prior baseline, logistic regression, and gradient boosting are compared using chronological training, validation, and later test data. Pending orders are excluded. Model inputs contain only assumed order-time information.
- **Next stock record:** The same classification approach estimates the next recorded stock state, with future-label dates purged across evaluation boundaries. Irregular stock records prevent presenting this as a fixed-day forecast.
- **Items sold and revenue:** Seasonal naive, recent mean, and Holt-Winters methods are compared on two rolling validation windows, followed by a separate final holdout. Daily calendars include zero-sale days. Measured errors and approximate range coverage are published.
- **Customer groups:** Actual customer-level purchase histories produce recency, frequency, and monetary features. Seeded KMeans chooses group count by silhouette, separately from the supplied customer labels.
- **Unusual days:** IsolationForest learns earlier daily patterns and highlights later deviations. There are no confirmed anomaly labels, so detection accuracy is not claimed.
- **Campaign results:** A click-rate baseline, Poisson regression, and gradient boosting estimate conversion counts after engagement is measured. Impossible counts are excluded from model training but remain visible in reporting.

Preprocessing is fitted inside training pipelines. Validation selects models; the final test never determines selection. Simple baselines are retained when learned models do not help. The measured order and stock evaluations currently retain their baselines and do not support ranking individual cases.

## Decisions and restocking

The offline recommendation engine prioritizes conflicting records, cancelled/returned order investigations, low-stock reviews, and campaign checks. Each task includes supporting numbers, a suggested responsible team, ordered steps, a metric to track, and a limitation.

The restock planner uses recent observed sales, recorded lead/delay times, a review interval, and an explicit safety allowance. Conflicting, future-dated, or old stock records block quantity suggestions. Optional budget allocation is an illustrative policy, not proof of mathematically optimal inventory or savings.

Recommendations are produced locally through transparent rules and supporting calculations. Predictive models are trained and evaluated independently on the supplied records.

## Interface and reproducibility

Streamlit provides the original multipage interface; Plotly provides trends, comparisons, outcome breakdowns, and stock status views. Financial figures are shown in ₹, while quantities remain items. Each source's valid filter scope is explicit.

Run `python -m vaultdata.ml.evaluate --output reports` to rebuild the source checksums, model comparisons, metrics, predictions, forecasts, customer assignments, unusual-day evidence, and restock scenario. Run `python -m pytest -q` for contract, leakage, calculation, safeguarding, and UI checks. A CI workflow performs the same operations without credentials.

The source is synthetic and its currency is unspecified; rupee display is a presentation assumption without conversion. Missing outcome-resolution times, actual cancellation reasons, campaign attribution, stock movements, lost demand, open supplier orders, and cost records limit operational claims. Full assumptions, model cards, and measured results accompany the code.
