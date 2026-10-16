"""Consistent number/currency formatting.

Amounts are displayed in rupees using Indian digit grouping, as requested.
The source currency is unspecified; no exchange-rate conversion is applied.
"""
from __future__ import annotations

from vaultdata.config import CURRENCY_SUFFIX, CURRENCY_SYMBOL

MONEY_COLUMNS = {'Revenue','Completed revenue','Revenue from completed orders','Affected value','Cancelled + returned value','Completed discounts','Discounts on completed orders','Average order value','Avg Transaction Value','Spend','spend','Cost per conversion','Cost per reported conversion','Net order value','Order value after discounts','Order value after discount','Order value before discount','Discount amount','Selling price per unit','Cost per unit','Listed price','Recorded product cost','Order value minus recorded product cost','unit_price','unit_cost','list_price'}


def format_currency(value: float, decimals: int = 2, suffix: bool = True) -> str:
    if value is None:
        return "N/A"
    # Indian digit grouping: 1,23,456.78. This is a presentation choice, not FX conversion.
    whole, dot, fraction = f"{abs(value):.{decimals}f}".partition(".")
    if len(whole) > 3:
        leading, last = whole[:-3], whole[-3:]
        groups = []
        while leading:
            groups.insert(0, leading[-2:])
            leading = leading[:-2]
        whole = ",".join(groups + [last])
    formatted = f"{'-' if value < 0 else ''}{CURRENCY_SYMBOL}{whole}{dot}{fraction}"
    return f"{formatted} {CURRENCY_SUFFIX}" if suffix and CURRENCY_SUFFIX else formatted


def compact_currency(value: float) -> str:
    if abs(value) >= 1e7:
        return f"₹{value/1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value/1e5:.2f} L"
    return format_currency(value, decimals=0)


def rupee_table(df):
    """Format monetary fields without modifying the underlying numbers."""
    return df.style.format({name:format_currency for name in df.columns if name in MONEY_COLUMNS}, na_rep='—')


def format_number(value: float, decimals: int = 0) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_percent(value: float | None, decimals: int = 1, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"
