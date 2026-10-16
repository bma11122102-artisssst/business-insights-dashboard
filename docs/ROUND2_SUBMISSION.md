# Round 2 submission answers

Source: [official Round 2 requirements](https://datathon-xi.vercel.app/round2.html), checked 16 October 2026. This is preparation text, not a submitted form. Enter team names, registration numbers, phone numbers and contact email yourself; these are not inferred from GitHub.

## Project and GitHub

| Form field | Answer |
|---|---|
| Track | Track 4 · Business |
| Product name | LeakLens |
| One-line pitch | Retail decision support that connects sales, stock and marketing evidence to locally trained predictions and step-by-step actions. |
| Public repository | https://github.com/bma11122102-artisssst/business-insights-dashboard |
| Branch | main |
| Model type | Trained from scratch |

## What does your model predict?

Our main supervised model estimates reported campaign conversion counts from measured spend, impressions, clicks, weekday/month, channel and category. It is fitted locally on the provided campaign records. It is a diagnostic after clicks are measured, not a pre-launch prediction. We also fit order-outcome classifiers, next-record stock classifiers, daily unit/revenue forecasts, purchase-history customer groups and unusual-day detection. Order and stock classifiers did not beat their prior baselines, so we explicitly do not claim individual risk ranking. A separately trained external retail demand benchmark uses UCI Online Retail daily item sales without mixing the two businesses.

## Algorithm used

Histogram gradient boosting with Poisson loss for campaign counts; Poisson regression and a click-rate baseline are compared on validation MAE. Additional models include logistic regression, classification gradient boosting, KMeans on standardized log-RFM, IsolationForest, Holt-Winters and recent-mean/weekly forecast baselines. Model parameters are fitted locally; no pretrained model or hosted inference is used. Recommendations and restock safeguards use explicit business rules and calculations, not a falsely labeled learned model.

## Training code file in your repo

`train.py` is the runnable entry point. Actual training and evaluation: `vaultdata/ml/evaluate.py`; campaign `.fit()` implementation: `vaultdata/ml/campaigns.py`; train-only preprocessing and time splitting: `vaultdata/ml/common.py`. Data loading: `vaultdata/data/track4.py`. External benchmark: `vaultdata/ml/external.py`.

## Result, if measured

On held-out provided data, campaign conversion MAE is 361.37 versus 447.68 for the click-rate baseline (19.3% lower). All-category daily item MAE is 14.65 versus 19.57 for the weekly baseline (25.1% lower); daily revenue MAE is 2776.65 versus 3369.33 (17.6% lower). Selection uses earlier validation data, not the final test. Full dates, eligible rows, metrics, source hashes and predictions are in `reports/evaluation.json` and CSV artifacts. External benchmark results are reported separately in that JSON and the Model checks page; they are not included in these Track 4 figures.

## APIs, keys and pretrained models

Select **None** for external inference services in the current submitted version. The product trains and runs locally. No pretrained model weights are used. If the form asks what the API does, answer **Not applicable — current version has no hosted model integration**. Dataset downloads and GitHub hosting are infrastructure, not hosted model inference. No credentials are required for evaluation or dashboard use.

## Extra data used

UCI Online Retail, Daqing Chen (2015), DOI: 10.24432/C5BW33, CC BY 4.0. We derive customer-free daily aggregates from its original transaction workbook. The committed derived CSV, exact transformation, source checksum and attribution are in `data/external/uci_online_retail/` and `scripts/prepare_external_retail.py`. It is an independent demand benchmark, never merged into official business totals or used as proof of Track 4 model transfer.

The original repository's supermarket sample remains an optional demonstration mode; it is not part of the Track 4 training/evaluation cohort. The user-upload mode can read other files but those are not bundled training data.

## Which dataset files does your code use?

All five official Track 4 files: `transactions.csv`, `customers.csv`, `products.csv`, `inventory.csv`, `campaigns.csv` in `data/track4/04_business_money_leak/`. Additional derived benchmark: `data/external/uci_online_retail/daily_sales.csv`. See README for file-level roles and joins.

## How to run, one line

`python -m pip install -r requirements.txt && python -m streamlit run streamlit_app.py`

Python 3.12 is tested. For local training: `python train.py --output reports`. Full setup and verification commands are in README.

## Before submitting

- Confirm the public repository and `main` branch contain the final commit, screenshots and source files.
- Inspect the latest GitHub Actions result; a checked-in workflow is not proof of a successful run.
- Review the README screenshots, sample predictions and model/data declarations.
- Complete personal/team fields and tick declarations only after checking them.
- The official page says the last commit before **4:30 PM IST, 16 October 2026** is judged; later pushes are ignored. Confirm submission timing with organizers. We cannot guarantee acceptance of a late revision.

There is **no live demo** according to the official Round 2 page. The repository itself is the review artifact; the demo document is a self-guided walkthrough.
