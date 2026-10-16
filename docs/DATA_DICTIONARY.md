# Data dictionary and contracts

The authoritative inputs are the five unchanged CSV files under `data/track4/04_business_money_leak/`. `reports/evaluation.json` records row counts, fields, primary keys, and SHA-256 hashes. There are no real personal or business records in this synthetic sample.

## customers.csv — one row per customer (3,000)

| Field | Meaning / use |
|---|---|
| `customer_id` | Unique non-null key. Connects transactions and actual customer purchase history. Never a classifier input. |
| `region` | Profile region. Sales/customer breakdown and assumed order-time region feature. Not a warehouse region. |
| `customer_segment` | Supplied profile label. Used for descriptive breakdowns, not as a target for independently derived RFM groups. Excluded from order prediction because profile timing is unknown. |
| `signup_date` | ISO date. Cross-checked against order timestamps; 797 order/signup conflicts are reported. Excluded from order-time features. |
| `preferred_channel` | Supplied preferred shopping channel. Descriptive comparison with recorded order channel; no claim that it caused customer behavior. |

## products.csv — one row per product (250)

| Field | Meaning / use |
|---|---|
| `product_id` | Unique non-null key for transaction and inventory joins. Not used as a predictive ID shortcut. |
| `category` | Product category. Breakdowns, filters, forecasts, stock/campaign context. |
| `unit_cost` | Nonnegative generated product cost. Displayed illustrative cost arithmetic and restock example budget. Not audited accounting cost. |
| `list_price` | Nonnegative product price reference, preserved for inspection. Not substituted for transaction selling price and not used to fabricate discounts. |
| `supplier_lead_days` | Nonnegative recorded supplier delivery time. Stock-state features and scenario lead-time calculation. |

## transactions.csv — one row per recorded order (18,000)

| Field | Meaning / use |
|---|---|
| `transaction_id` | Unique non-null order key. Evidence/export only, not a feature. |
| `customer_id` | Foreign key to customers; must resolve. |
| `product_id` | Foreign key to products; must resolve. |
| `timestamp` | ISO datetime. Daily aggregates, whole-day temporal partitions, order-time hour/weekday/month. |
| `quantity` | Positive units. Quantity forecasts and historical booked-unit features. |
| `unit_price` | Nonnegative actual transaction selling price before discount. |
| `discount_pct` | Fraction in [0,1], despite its source name. Actual discount arithmetic and order-time feature. |
| `status` | Completed, Cancelled, Returned, Pending. Classification target and sales accounting filter. Pending is unresolved and excluded from outcome-model fitting. |
| `channel` | Shopping channel. Actual order context, filters, classifier feature. |
| `payment_method` | Recorded payment method. Order analysis and assumed order-time feature. |

The adapter retains source identifiers and metadata and adds the original dashboard's canonical columns (`Date`, `Total`, `Quantity`, `Product line`, `Status`, `Region`, `Channel`, etc.). `Date` is normalized to a calendar day; `Hour` comes from the original timestamp. Net value = quantity × unit_price × (1−discount_pct). Raw inputs are not overwritten.

## inventory.csv — one product observation on a recorded date (5,000)

| Field | Meaning / use |
|---|---|
| `inventory_record_id` | Unique observation key. Breaks ties deterministically for multiple observations of a product on one date. |
| `product_id` | Foreign key to products; must resolve. |
| `date` | ISO observation date. Irregular spacing; not a daily inventory ledger. |
| `stock_on_hand` | Nonnegative units recorded. Actual display, current-record features, planning scenario. |
| `reorder_threshold` | Nonnegative supplied restock level. Current-rule comparison and stock features. |
| `stockout_flag` | Binary reported state. Conflicts with positive quantities are audited. Excluded as a current-model feature; the **next** record's flag/zero stock defines the future label. |
| `supplier_delay_days` | Nonnegative recorded delay. Display, stock feature, scenario lead-time assumption. |

114 repeated product/date observations exist. Next-record modeling collapses them by keeping the last record ID, then shifts labels strictly to a later observation. Latest-stock UI uses date plus record ID. Future-label dates crossing validation/test boundaries are purged from the earlier partition.

## campaigns.csv — one campaign report (1,200)

| Field | Meaning / use |
|---|---|
| `campaign_id` | Unique key. Evidence/export only, not a predictive feature. |
| `date` | ISO report date. Chronological split and contextual aggregate key. |
| `channel` | Campaign channel. Includes Email/Social, which do not occur as transaction channels in this sample. Missing transaction matches remain missing, not attributed zero revenue. |
| `category` | Campaign category. Compared with category-level sales context, never treated as an order attribution key. |
| `spend` | Nonnegative recorded spend. Efficiency metrics and diagnostic model input. |
| `impressions` | Nonnegative recorded ad views. Count-chain audit and measured diagnostic input. |
| `clicks` | Nonnegative clicks. Count-chain audit, measured input, baseline exposure. Not available before a campaign runs. |
| `conversions` | Nonnegative reported outcomes. Diagnostic target; not unique customers or attributed orders. Excluded from input features. |

The cleaned modeling cohort requires `0 < clicks ≤ impressions` and `conversions ≤ clicks`. The original reports remain visible, with warnings. 171 rows are excluded (including zero-click rows); 1,029 remain. Rates with a zero denominator are unavailable rather than replaced by fabricated values.

## Structural failures versus quality warnings

Missing required columns/values, empty files, repeated primary keys, unknown customer/product references, invalid ISO dates, nonfinite/negative numeric values, nonpositive quantities, invalid discounts, unknown order statuses, and nonbinary stock flags stop loading with a clear error. Signup chronology, stock contradictions, impossible campaign chains, repeated product/date observations, and generated-cost inconsistencies are retained, audited, and handled explicitly by each model.
