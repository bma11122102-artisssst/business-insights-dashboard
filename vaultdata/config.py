"""Central configuration: paths, column mapping, and display constants.

Keeping this in one place is what lets the rest of the codebase refer to a
stable set of column names (see COLUMN_ALIASES) regardless of what a
user-uploaded CSV happens to call them, and lets formatting/branding change
in one spot instead of dozens.
"""
from __future__ import annotations

from pathlib import Path

APP_TITLE = "NTR Business Intelligence Dashboard"
APP_TAGLINE = "The Money Leak · Find the problems. Decide what to do next."
APP_STATUS = "DATATHON Track 4 · Sample data for learning"
BRAND_LINE = "NTR · Business Intelligence"
VISIVAULT_URL = "https://www.visivaultanalytics.com/"

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = REPO_ROOT / "assets" / "leaklens-logo.svg"
DEFAULT_DATASET_PATH = REPO_ROOT / "data" / "supermarket_sales.csv"

# Display rupees as requested. Original sample currency is unspecified;
# this is a presentation assumption, not an exchange-rate conversion.
CURRENCY_SYMBOL = "₹"
CURRENCY_SUFFIX = ""

# Canonical column names the rest of the app is written against, and the
# alternate header names a real-world export might use instead. `loader.py`
# renames whatever it finds on the left to the canonical name on the right.
# Kept intentionally short -- covers the common naming variants for this kind
# of retail-transactions export without trying to guess every possibility.
COLUMN_ALIASES: dict[str, list[str]] = {
    "Invoice ID": ["invoice id", "invoice_id", "transaction id", "transaction_id", "order id"],
    "Branch": ["branch", "store", "location code"],
    "City": ["city", "store city"],
    "Customer type": ["customer type", "customer_type", "membership"],
    "Gender": ["gender"],
    "Product line": ["product line", "product_line", "category", "product category"],
    "Unit price": ["unit price", "unit_price", "price"],
    "Quantity": ["quantity", "qty", "units"],
    "Tax 5%": ["tax 5%", "tax", "tax_amount"],
    "Total": ["total", "sales", "revenue", "total_sales", "total sales", "amount"],
    "Date": ["date", "transaction_date", "order_date", "order date"],
    "Time": ["time", "transaction_time", "order_time"],
    "Payment": ["payment", "payment method", "payment_method"],
    "cogs": ["cogs", "cost of goods sold"],
    "gross income": ["gross income", "gross_income", "profit"],
    "Rating": ["rating", "satisfaction", "review score"],
}

# A dataset must contain these (after alias resolution) for the app's core
# analytics to run at all -- everything else is optional and features that
# depend on a missing optional column are simply hidden rather than crashing.
REQUIRED_COLUMNS = ["Date", "Total", "Quantity", "Product line"]
OPTIONAL_COLUMNS = [c for c in COLUMN_ALIASES if c not in REQUIRED_COLUMNS]

# Weekly seasonality is the only cycle 89 days of daily retail data can
# support reliably (not enough history for a monthly/annual cycle).
FORECAST_SEASONAL_PERIOD = 7
FORECAST_HORIZON_OPTIONS = [7, 14, 30, 60]
FORECAST_TEST_HOLDOUT_DAYS = 14

SEGMENTATION_K_RANGE = range(2, 7)
