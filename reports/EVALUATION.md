# Track 4 — Reproducible evaluation

Generated: 2026-10-16T10:43:31.994876+00:00

All results below are measured on the supplied synthetic files. Model selection uses validation data; final test data is reserved for evaluation. No cloud key or language-model request is used.

## Supervised results

| Task | Validation-selected method | Test error | Baseline error | Interpretation |
|---|---|---:|---:|---|
| Order outcomes | prior_baseline | 0.602720 (log_loss) | 0.602720 | Baseline retained; no individual predictive lift established. |
| Next recorded stock state | prior_baseline | 0.441291 (log_loss) | 0.441291 | Baseline retained; no individual predictive lift established. |
| Campaign conversion counts | gradient_boosting | 361.368850 (mae) | 447.675758 | Held-out improvement observed. |
| Daily completed revenue | recent_mean | 2776.654913 (mae) | 3369.333500 | Held-out improvement observed. |

## Daily unit forecasts

| Category | Selected method | Test MAE (units/day) | Seasonal baseline MAE | 80% range coverage |
|---|---|---:|---:|---:|
| All categories | recent_mean | 14.653 | 19.571 | 92.9% |
| Beauty | holt_winters | 5.350 | 7.500 | 64.3% |
| Electronics | recent_mean | 5.837 | 8.714 | 71.4% |
| Fashion | holt_winters | 6.109 | 7.786 | 85.7% |
| Grocery | recent_mean | 6.602 | 12.357 | 85.7% |
| Home | recent_mean | 6.214 | 8.857 | 64.3% |
| Sports | recent_mean | 5.786 | 9.214 | 92.9% |

## Unsupervised diagnostics

- Customer KMeans: 2971 customers; k=2; silhouette=0.3660; Davies–Bouldin=1.0429. These measure separation, not prediction accuracy.
- IsolationForest: 10 flagged of 73 later days. No anomaly ground truth exists; precision/recall cannot be claimed.

## Data audit

| Check | Count | Handling |
|---|---:|---|
| orders_before_customer_signup | 797 | Keep orders for sales totals; exclude signup-derived features from order prediction. |
| stock_flag_with_positive_units | 760 | Show the conflict. Do not silently overwrite stock or claim a verified physical stockout. |
| campaign_conversions_above_clicks | 88 | Keep raw analysis visible; exclude impossible count chains from campaign model training. |
| campaign_clicks_above_impressions | 84 | Keep raw analysis visible; exclude impossible count chains from campaign model training. |
| completed_orders_below_recorded_cost | 5315 | Costs and prices are independently generated; no audited profit or savings claims. |
| duplicate_product_inventory_dates | 114 | For next-observation modeling keep the last record ID on a product/date; record the exclusion count. |

## Separate external retail benchmark

UCI Online Retail, Daqing Chen (2015), CC BY 4.0, DOI: 10.24432/C5BW33. Customer-free daily aggregates; never pooled with Track 4.
Independently fitted daily-unit method: holt_winters; test MAE 9714.423 items versus weekly baseline 11052.429. Measured approximate 80% range coverage: 78.6%.
Final test: 2011-11-26 to 2011-12-09. This is a separate fit, not proof that the Track 4 model transfers to another business.

## Reproduce

```powershell
python -m vaultdata.ml.evaluate --output reports
python -m pytest -q
```

See `evaluation.json` for exact features, dates, model-selection scores, confusion matrices, exclusions, seeds, environment versions, and dataset SHA-256 hashes. CSV files contain held-out predictions, future forecasts, customer assignments, and observed evidence.

## Limits

Synthetic data does not establish real-world generalization. Stock horizons are irregular; campaign models use measured clicks; sales forecasts estimate observed completed sales; missing operational records prevent causal savings claims or validated inventory optimization. Rupee display is a presentation assumption, not currency conversion.
