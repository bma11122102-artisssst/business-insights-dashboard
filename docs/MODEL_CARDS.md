# Model cards

All models use the supplied synthetic Track 4 files, seed 42, and inspectable Python implementations. Measured values are generated in [reports/EVALUATION.md](../reports/EVALUATION.md); exact parameters, dates, features, baseline results, and confusion matrices are in [reports/evaluation.json](../reports/evaluation.json). No production performance is implied.

## 1. Order outcomes

- **Question:** Can order-time information distinguish Completed, Cancelled, and Returned outcomes?
- **Code:** `vaultdata/ml/order_risk.py`.
- **Data:** Transactions plus validated customer-region and product-category joins. 918 Pending rows excluded; 17,082 resolved rows eligible.
- **Features:** Quantity, transaction unit price, discount fraction, hour, weekday, month, category, region, channel, payment method.
- **Excluded:** IDs, target Status, derived margins/revenue, signup timing, supplied customer segment, future records. Historical outcome time is unavailable; see assumptions for the limitation of treating resolved outcomes as known at date cutoffs.
- **Candidates:** Dummy prior; logistic regression (max_iter=1000); histogram gradient boosting (100 iterations, 10 leaves, L2=10, early stopping disabled).
- **Evaluation:** Whole-day 60/20/20 chronological split, with a documented 30-day assumed outcome-maturation window purging near-boundary labels; preprocess inside each training pipeline; validation log loss selects; selected model and baseline refit on eligible train+validation; final test once. Actual resolution times are missing, so the maturation assumption does not prove operational label availability. Log loss, macro-F1, balanced accuracy, risk Brier, ROC-AUC, average precision, and confusion matrix are recorded.
- **Observed decision:** Prior baseline retained. No useful individual ranking established. Pending rows receive only a broad rate estimate; the UI warns against calling individual orders high-risk.
- **Interpretation:** If a learned model is selected, permutation importance measures test log-loss changes under feature shuffling. This is not causal explanation. With a prior model, feature importance is empty rather than invented.

## 2. Next recorded stock state

- **Question:** Will the next recorded observation report a stockout state?
- **Code:** `vaultdata/ml/stock_risk.py`.
- **Data preparation:** Product metadata joins inventory. Collapse 114 repeated product/date records by last observation ID. Shift target to the next strictly later date; latest records have no future label. 4,636 labeled transitions remain before date-boundary purging.
- **Target:** Next record's stockout_flag=1 or next stock_on_hand≤0. This predicts a reported state, not verified physical availability.
- **Inputs:** Current stock, supplied restock level, current delay, product supplier lead, previous stock, days since previous observation, booked units in the prior 7/30 days, calendar day/month, category.
- **Leakage controls:** Current flag, next quantity/flag/date, target, and future order quantities are not inputs. Booked orders are counted strictly before the observation day and do not depend on later final status. Every train label must predate validation; every validation label must predate test. 494 boundary-crossing transitions are purged in this run.
- **Candidates:** Prior; logistic regression; gradient boosting (100 iterations, 7 leaves, L2=20). Validation log loss selects.
- **Observed decision:** Prior baseline retained; no useful individual stock-risk ranking. Irregular observation gaps are published, so scores are not advertised as next-week risk.
- **Limit:** All 760 positive stockout flags conflict with positive quantities in this synthetic sample. The target is noisy reported state. Operational use needs reliable snapshots and movements.

## 3. Daily units and revenue

- **Question:** What completed sales may occur over the next days?
- **Code:** `vaultdata/ml/demand.py`; interactive quantities in `views/unit_forecast.py`.
- **Data:** Complete daily calendars of completed units, globally and for each of six categories; completed revenue globally. No-sale days become zero. No algebraically circular quantity regression is used.
- **Candidates:** Seven-day seasonal naive, trailing 28-day mean, additive-trend/additive-weekly Holt-Winters. Negative values clipped to zero.
- **Selection:** Two rolling 14-day validation blocks immediately before a separate final 14-day test. Candidate MAE is averaged across validation days; final test cannot change model choice or range calibration.
- **Metrics:** MAE/RMSE/WAPE; baseline MAE; final empirical 80% range coverage and width. CSVs include actuals, chosen estimates, baseline, ranges, and future dates.
- **Intervals:** 80th percentile of absolute validation errors, pooled across steps. Approximate and based on only 28 default residuals. Some measured category coverage is below nominal; future long-horizon coverage is not established.
- **Limit:** Observed completed sales are not uncensored demand; missing stock availability means lost demand is unknown. Stable synthetic data can legitimately favor a mean forecast.
- **Existing feature:** The original revenue-only Holt-Winters UI remains, with its own time-ordered validation and simulation interval. It is not silently described as the selected offline comparison model.

## 4. Customer buying groups

- **Question:** Which customers have similar recent purchasing behavior?
- **Code:** `vaultdata/ml/customers.py`.
- **Inputs:** Customer-level recency from snapshot date, unique completed-order frequency, net monetary sum. Exclude future and Pending records; exclude customers with no completed purchases.
- **Method:** `log1p`→StandardScaler→KMeans, candidate k=2…6, n_init=10, seed 42. Silhouette on a deterministic sample of up to 1,000 chooses k. Report Davies–Bouldin and actual group summaries.
- **Observed:** 2,971 buyers, k=2, silhouette approximately 0.366. Derived labels describe spending/recency relative to the selected population and remain separate from supplied customer_segment.
- **Limit:** No ground-truth customer types or future-retention labels. Separation is not predictive accuracy or proof that marketing to a group will work. The model is a snapshot analysis, not a future classifier.

## 5. Unusual historical days

- **Question:** Which later days look unusual compared with earlier daily records?
- **Code:** `vaultdata/ml/anomalies.py`.
- **Inputs:** Daily completed revenue, order count, cancellation rate, return rate, average recorded discount, units sold.
- **Method:** IsolationForest, 150 trees, training contamination 5%, seed 42. Fit first 80% of days only; score last 20% without refitting.
- **Outputs:** Unusualness score, flag, original daily values, and two largest deviations relative to training medians/IQR. The deviations are descriptive context, not a causal attribution of the model's score.
- **Observed:** 10 of 73 later days flagged. **No labeled anomalies exist**, so precision/recall or fraud-detection accuracy are not available.
- **Limit:** Retrospective monitoring of observed outcomes, not forecasting future failures. Threshold is a chosen training heuristic.

## 6. Campaign conversion-count diagnostic

- **Question:** Given measured engagement, what conversion count is typical enough to benchmark a campaign record?
- **Code:** `vaultdata/ml/campaigns.py`.
- **Eligibility:** `0 < clicks ≤ impressions` and `conversions ≤ clicks`. 171 rows excluded; 1,029 eligible. Raw analysis still shows originals and warnings.
- **Count assumption:** Comparable-period counts and at most one conversion per click define this cohort. Predictions are bounded to [0, clicks]. The raw source does not establish conversion semantics; repeated/view-through conversions would need a different definition.
- **Inputs/timing:** Measured spend, ad views, clicks, weekday/month, channel, category. These are known only after measurement, so this is **not pre-launch forecasting**. No conversion-derived ratio enters features.
- **Candidates:** Training conversions/click rate × later clicks; Poisson regression (alpha=1,max_iter=1000); Poisson-loss histogram gradient boosting (100 iterations,7 leaves,L2=20).
- **Evaluation:** Whole-day chronological 60/20/20; validation MAE selects; train+validation refit; later held-out MAE/RMSE/WAPE. Selected gradient boosting test MAE≈361.37 vs baseline≈447.68.
- **Limit:** Reported conversions are not unique buyers or attributed orders. Results do not establish incremental campaign revenue, ROAS, or a causal budget-allocation recommendation.

## 7. Restock scenario (policy, not trained optimizer)

- **Code:** `vaultdata/analytics/restocking.py`.
- **Inputs:** Thirty-day observed completed units, supplied stock, supplier lead/delay, review interval, safety multiplier, optional example budget.
- **Safeguards:** Conflicting flag/quantity records, future records, and records older than 14 days block suggestions. Inventory planning respects inventory's date/category scope; customer filters cannot artificially shrink demand against business-wide stock.
- **Limit:** Missing orders already on the way, actual stock movements, ordering/holding costs, and unobserved demand prevent claiming optimal quantities, service guarantees, or evaluated savings. Optional budget allocation is a transparent coverage-priority scenario.

## 8. External retail demand benchmark

- **Data:** UCI Online Retail, Chen (2015), CC BY 4.0. 541,909 source transactions; 530,104 positive-sale rows aggregated into 374 calendar dates. Source/derived SHA-256 recorded in `data/external/uci_online_retail/provenance.json`.
- **Target:** recorded positive-sale daily item units. All countries combined; no customer IDs retained. Nonpositive quantities/prices and cancellation-prefixed invoices excluded. Missing calendar days filled with zero recorded sales; final source date can be partial.
- **Training:** same seasonal-naive/recent-mean/Holt-Winters candidate family, independently fitted on this business. Two earlier 14-day validation blocks select the method, final 14 days measure MAE/RMSE/WAPE and range coverage. No Track 4 data enters this fit.
- **Limit:** This checks the forecasting workflow on another retail series, not transfer of a fixed Track 4 model. Zero sales does not establish zero demand, positive sales are not net revenue, and performance need not beat the baseline. GBP values are never mixed with the challenge's rupee presentation.
- **Code/results:** `vaultdata/ml/external.py`; `reports/evaluation.json` under `external_benchmark`; external holdout/forecast CSVs and Model checks expander.
