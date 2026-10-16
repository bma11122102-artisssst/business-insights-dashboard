# External retail benchmark

**Attribution:** Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33

- Source: https://archive.ics.uci.edu/dataset/352/online+retail
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
- Original download: https://archive.ics.uci.edu/static/public/352/online+retail.zip
- Changes: exclude cancellation-prefixed invoices, nonpositive quantity/price and missing dates; aggregate all countries by calendar date; fill dates with no records with zero recorded sales. No deduplication. Customer identifiers and item descriptions are not retained in the derived file.
- `daily_sales.csv` contains daily units, invoice count and positive recorded sales in **GBP**. This is not net revenue after returns. GBP amounts are never displayed as rupees or mixed into Track 4 totals.
- `provenance.json` records source/derived checksums, row counts and date bounds.

## Purpose

Fit and evaluate the demand methods on an additional retail history. This is a separate training/evaluation experiment, not a test of a fixed Track 4 model transferred to a new business. It does not improve or change the official dashboard's business totals. No customer-level data is committed.

The demand benchmark uses **units only**, two rolling validation windows and a final 14-day holdout. Zero-sales days may reflect missing observations or closure; recorded sales do not measure uncensored demand. The last source day can be partial. There is no guarantee of beating the seasonal baseline; results remain visible either way.

## Rebuild

Download the original archive from UCI, then:

```bash
python -m pip install openpyxl==3.1.5
python scripts/prepare_external_retail.py --archive /path/to/online+retail.zip
python train.py --output reports
```

The app and standard offline evaluation read the committed aggregate directly and do not need openpyxl, a network connection or the full workbook. This derived file is an adaptation under CC BY 4.0; the repository's MIT code license does not replace the dataset license.
