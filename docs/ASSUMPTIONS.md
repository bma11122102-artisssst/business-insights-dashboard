# Assumptions, calculations, and evaluation protocol

## Accounting and presentation

1. Order gross value = `quantity × unit_price`. Discount = gross × `discount_pct`. Net value = gross − discount.
2. Completed revenue sums net value for `Completed` only. Cancelled, Returned, and Pending remain separate statuses. The data has no refund timing, tax/shipping/cost recovery, return-condition, or accounting ledger, so affected value is not audited loss or guaranteed recovery.
3. Recorded product cost = quantity × product unit_cost. Sales minus that cost is only illustrative and excludes marketing, fulfillment, overhead, and other expenses. Independently generated cost/price values produce unrealistic margins.
4. ₹ is a user-selected display assumption applied to the supplied numbers. No original currency or foreign-exchange conversion is inferred. Counts remain units/items and percentages remain percentages.

## Point-in-time modeling

- Whole days, not randomly shuffled rows, define earlier training (60%), validation (20%), and later test (20%) partitions for order/campaign/stock models.
- Every imputer, scaler, encoder, and learned estimator is fitted inside its training pipeline. Unseen validation/test categories are ignored safely by the encoder.
- Candidate selection uses validation only. The chosen pipeline and baseline are then refitted on train+validation before final-test scoring. After scoring is complete, a deployment-only fit on all resolved labels can generate estimates for unresolved/latest records; those estimates are not mixed into the reported test metrics.
- Resolved order statuses have **no resolution timestamps**. A fixed, documented **30-day assumed outcome-maturation delay** purges labels close to order-model partition boundaries. It cannot prove actual label availability: a real deployment needs outcome timestamps and a measured maturation/embargo policy. The next-stock benchmark does have future observation dates and explicitly purges cross-boundary labels. Pending/latest deployment estimates are generated after evaluation from the current snapshot, not claimed as historical predictions made at record creation.
- Current profile region/category/payment are assumed available when an order is placed. Supplied customer segments and signup-derived features are excluded from the order model because profile timing is unknown and signup dates conflict with 797 orders.
- No ID, final status, future stock, derived outcome rate, future customer aggregate, or campaign conversion target is an order input. Next-record stock inputs exclude the current stockout flag and all next-record fields.
- Stock demand context uses **booked order quantities before the observation day**, irrespective of later final status. This avoids treating a later-resolved status as information available at that earlier observation.

## Forecasting

- Completed sales quantities/revenue are aggregated to a complete calendar, filling no-sale dates with zero. They are observed sales, not unobserved demand during stockouts.
- The unit/revenue comparison reserves the last 14 days for the final test and uses the two preceding 14-day blocks for rolling validation. Every fold trains strictly before its validation dates. Selection minimizes combined validation MAE.
- Seasonal naive repeats the last seven observed values recursively. Recent mean repeats the last 28-day mean. Holt-Winters fits additive trend/weekly seasonality. Negative forecasts are clipped to zero.
- A pooled 80th percentile of absolute validation errors supplies approximate 80% forecast ranges. The test is never used to set width. Only 28 default calibration observations exist; measured coverage can be below 80%, and constant-width long-horizon ranges are not empirically validated. The report publishes actual coverage.
- The original revenue-only Streamlit forecast remains available with its Holt-Winters simulation range; its UI validation is distinct from the fully benchmarked offline revenue/unit comparison. The Model checks page identifies the protocol used for each result.

## Customers and unusual days

- Customer groups use only completed purchases on/before the chosen snapshot date. Recency is measured from that date, frequency counts unique completed orders, monetary value sums their net value. `log1p`, standardization, and seeded KMeans form 2–6 candidate groups; silhouette selects k. Customers without completed purchases are not clustered.
- Supplied profile segments are descriptive source labels; they are not ground truth for the independent groups. Silhouette/Davies–Bouldin measure separation, not predictive accuracy or economic value.
- IsolationForest trains on the earliest 80% of daily aggregates and scores the later 20%. A 5% training-contamination parameter is an explicit heuristic. No labeled anomalies exist; no precision/recall, fraud detection, or causal claim is supported. Displayed reasons are deviations from earlier medians/IQR, not causal model explanations.

## Stock and restocking

- Current status is reported out of stock if flagged or stock ≤ 0; otherwise running low if stock ≤ supplied restock level; otherwise above restock level. A reported flag can conflict with units, and remains visible as a conflict.
- Next-record target = the next observation's flag is 1 or its stock ≤ 0. Date gaps are irregular (median/mean/max in the report), so this is not fixed-horizon stockout prediction.
- Planning lead = product supplier lead + recorded delay. Mean/std use 30 calendar days of completed sales, including zeros. Scenario trigger = μL + zσ√L. Target = ceil(μ(L+review) + zσ√(L+review)). At/below trigger, suggested units = max(0,target−recorded stock).
- Default review is 7 days and z=1.28. The normal-demand/safety approximation is a user assumption, not an established service guarantee. Contradictory, future-dated, or >14-day-old stock records block suggestions until checked.
- An optional example budget allocates units by ascending recorded stock coverage using the generated unit costs. This is not an optimal allocation or validated ROI. Open purchase orders, stock movements, MOQ, holding/ordering costs, lost demand, and true service outcomes are missing.
- Stock planning uses date/category-filtered transactions and stock, not a customer-region/channel subset against business-wide stock.

## Campaigns and recommendations

- The conversion model requires valid nonzero click chains and excludes 171 impossible/zero-click rows. Raw reporting retains all rows with warnings. The baseline applies the earlier aggregate conversions/click rate to later measured clicks.
- This diagnostic assumes comparable-period funnel counts and at most one conversion per click. The source does not establish those definitions; repeated or view-through conversions would require another cohort definition. Exclusions and output clipping to [0, measured clicks] enforce this explicit modeling assumption, not a correction to the original records.
- Spend, impressions, and clicks are measured inputs: the conversion estimator is a post-engagement diagnostic, **not a pre-launch prediction**. No revenue attribution or ROAS is calculated. Aggregate sales/campaign context joins unique date/category/channel aggregates, preventing multiplication of raw records.
- The offline action checklist uses transparent rules: stock contradictions first; largest affected category value next (High if ≥100 category orders, otherwise Medium); low-stock and campaign-efficiency reviews follow. These priorities are product heuristics, not calibrated risk scores or optimized business impact.

## Method references

- [scikit-learn: leakage and training pipelines](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn: time-series-aware evaluation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
- [IsolationForest reference](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [Official Track 4 brief](https://datathon-xi.vercel.app/problem-statements.html#track-4) and the supplied dataset README.

## External-data scope

The UCI daily aggregate is an independently fitted supplementary demand benchmark. It is not joined to Track 4 and its results cannot be combined with Track 4 error metrics. Cancellations/nonpositive rows are excluded; zeros mean no recorded positive sales, not confirmed zero demand. Its retained positive-sale GBP field is not net revenue and is not converted to rupees. Full attribution and provenance are committed alongside the derived data.
