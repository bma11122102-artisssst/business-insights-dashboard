# Track 4 implementation map

Source: [The Money Leak](https://datathon-xi.vercel.app/problem-statements.html#track-4). The brief requests decision support for business owners, retail/category managers, and operations teams. It lists possible approaches, not a requirement to claim every model is successful. The published 100-mark rubric is mapped to code and evidence in [JUDGING_EVIDENCE.md](JUDGING_EVIDENCE.md).

| Brief requirement | Working implementation | Verification |
|---|---|---|
| Identify revenue/operational problems | Completed-only revenue, cancelled/returned values, discount totals, stock status, marketing efficiency | `views/executive_overview.py`, `views/track4.py`; calculation and UI tests |
| Investigate likely drivers | Category/region/channel/customer breakdowns, weekly outcomes, supporting records; explicit missing-reason caveats | `vaultdata/analytics/sales.py`, `leakage.py`, Data page |
| Decide what to do next | Offline prioritized checklist with steps, owner role, evidence, success metric, limits | `vaultdata/analytics/action_plan.py`; `test_step_by_step_engine_works_without_cloud` |
| Use transactions, customers, products together | Many-to-one validated joins; order features; true customer purchase histories; cost/price consistency checks | `vaultdata/data/track4.py`, `audit.py`; schema/reference tests |
| Use inventory availability | Current recorded status, conflict warnings, supplier delays, future next-record evaluation, guarded restock scenarios | `vaultdata/ml/stock_risk.py`, `analytics/restocking.py`; future-feature and boundary tests |
| Use campaign context | Spend→views→clicks→reported conversions, count-chain validation, conversion-count model; aggregated contextual join with sales | `vaultdata/ml/campaigns.py`; `reports/campaign_sales_context.csv`; explicitly no revenue attribution |
| Forecast or unusual-change alert | Revenue and per-category unit forecasts, baseline selection, IsolationForest later-day flags | `vaultdata/ml/demand.py`, `anomalies.py`; final holdout predictions and diagnostics |
| Explain flags | Original values, rule definitions, source scope, validity warnings, supporting numbers, descriptive anomaly deviations | Stock/Recommendations/Model checks pages; downloadable reports |
| Customer segmentation | Independent customer-level KMeans using actual IDs and log-RFM, separate from supplied segment labels | `vaultdata/ml/customers.py`; `reports/customer_groups.csv` |
| Cancellation/return classification | Order-time features only, Pending excluded, validation-selected classifier/baseline, final-test probability metrics | `vaultdata/ml/order_risk.py`; `reports/order_holdout_predictions.csv` |
| Document costs/prices/returns/profit | Explicit formulas, synthetic cost-price inconsistencies, no guaranteed recovery/net-profit/ROAS claims | `docs/ASSUMPTIONS.md`, in-app How it works, `reports/EVALUATION.md` |

## Dataset-to-output traceability

- `customers.csv`: region and supplied segment breakdowns; ID-linked RFM; signup audit; preferred shopping channel in `customer_profile_context.csv`. Snapshot profile groups/signup timing are deliberately excluded from order-time classifier features.
- `products.csv`: category joins; cost arithmetic; list-price reference preserved in source previews; supplier lead times used in stock models/restock planning. A list-price difference is not fabricated as an actual transaction discount.
- `transactions.csv`: monetary/quantity totals; statuses; time splits; unit/revenue forecasts; customer history; daily anomalies; historical booked-unit inputs for stock models.
- `inventory.csv`: latest stock record per product; same-day collapse only for future-record modeling; current-stock inputs; next-record target; record age/contradiction safeguards.
- `campaigns.csv`: actual spend, impressions, clicks, and reported conversions; invalid chains visible; cleaned diagnostic training cohort; later-record predictions; date/category/channel context with transaction aggregates.

## No forced relationships

Campaign rows are not joined directly to individual orders. Customer region cannot filter inventory or campaigns. No inferred stock movement, actual cancellation reason, refund ledger, or campaign attribution is invented. Both sides are aggregated to unique date/category/channel keys before the contextual sales/campaign join, preventing accidental row multiplication.

## Baselines and unavailable claims

The measured order/stock classifiers did not establish individual ranking improvements. The report preserves this outcome instead of selecting a weak model to claim more AI. Restock planning is a transparent scenario, not a validated optimizer; inventory movements and costs needed for that claim are missing. Unsupervised diagnostics do not have ground-truth accuracy. See the generated report for numeric evidence.
