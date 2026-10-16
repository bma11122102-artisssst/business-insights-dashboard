"""Explainable investigations over the five official business tables."""
import pandas as pd
from vaultdata.viz.formatting import format_currency

def summarize(df: pd.DataFrame, group: str) -> pd.DataFrame:
    rows = []
    for label, part in df.groupby(group, observed=True):
        done = part[part.Status == 'Completed']
        affected = part[part.Status.isin(['Cancelled', 'Returned'])]
        rows.append({group:label, 'Orders':len(part), 'Completed revenue':done.Total.sum(), 'Affected value':affected.Total.sum(), 'Fallout rate %':100 * len(affected) / len(part), 'Completed discounts':done['Discount value'].sum()})
    columns = [group, 'Orders', 'Completed revenue', 'Affected value', 'Fallout rate %', 'Completed discounts']
    return pd.DataFrame(rows, columns=columns).set_index(group).sort_values('Affected value', ascending=False)

def filter_support(df: pd.DataFrame, state, *, campaign: bool = False) -> pd.DataFrame:
    out = df.copy()
    out['date'] = pd.to_datetime(out['date'])
    if state.date_range:
        start, end = state.date_range
        out = out[out.date.between(pd.Timestamp(start), pd.Timestamp(end))]
    if state.product_lines:
        out = out[out.category.isin(state.product_lines)]
    if campaign and state.channels:
        out = out[out.channel.isin(state.channels)]
    return out

def stock_snapshot(inventory: pd.DataFrame, products: pd.DataFrame, state) -> pd.DataFrame:
    inv = filter_support(inventory.merge(products, on='product_id', validate='many_to_one'), state)
    latest = inv.sort_values(['date', 'inventory_record_id']).drop_duplicates('product_id', keep='last').copy()
    latest['Signal'] = 'Healthy'
    latest.loc[latest.stock_on_hand <= latest.reorder_threshold, 'Signal'] = 'Reorder'
    latest.loc[(latest.stockout_flag == 1) | (latest.stock_on_hand <= 0), 'Signal'] = 'Stockout signal'
    return latest.sort_values(['stock_on_hand','product_id'])

def campaign_metrics(campaigns: pd.DataFrame, state) -> pd.DataFrame:
    campaigns = filter_support(campaigns, state, campaign=True)
    grouped = campaigns.groupby('channel')[['spend','impressions','clicks','conversions']].sum()
    grouped['Cost per conversion'] = grouped.spend.div(grouped.conversions.replace(0, float('nan')))
    grouped['CTR %'] = 100 * grouped.clicks.div(grouped.impressions.replace(0, float('nan')))
    grouped['Conversion rate %'] = 100 * grouped.conversions.div(grouped.clicks.replace(0, float('nan')))
    return grouped.sort_values('Cost per conversion', ascending=False)

def findings(df, stock, campaigns):
    result = []
    if not df.empty:
        ranked = summarize(df, 'Product line')
        label, top = next(iter(ranked.iterrows()))
        if top['Affected value'] > 0:
            result.append({'area':'Sales', 'finding':f'{label} has the highest value of cancelled or returned orders.', 'evidence':f"Cancelled or returned value: {format_currency(top['Affected value'])}; {top['Fallout rate %']:.1f}% of {int(top['Orders']):,} orders were cancelled or returned.", 'action':'Ask the team why orders were cancelled and check returned products for quality or delivery problems. The files do not include these reasons, so check them before making changes.', 'basis':'Based on recorded orders. This does not tell us how much money can be recovered.'})
    risks = stock[stock.Signal != 'Healthy']
    if len(risks):
        result.append({'area':'Stock','finding':f'{len(risks)} products need a stock check.', 'evidence':f"{int((stock.Signal == 'Stockout signal').sum())} products are reported out of stock; {int((stock.Signal == 'Reorder').sum())} others are running low.", 'action':'Check current stock, when the record was last updated, and how long the supplier takes to deliver before ordering more.', 'basis':'Uses the latest stock records in your chosen dates. Stock by region is not available.'})
    valid = campaigns.dropna(subset=['Cost per conversion'])
    if len(valid) >= 2:
        high = valid['Cost per conversion'].idxmax(); low = valid['Cost per conversion'].idxmin()
        if valid.loc[high, 'Cost per conversion'] > valid.loc[low, 'Cost per conversion']:
            result.append({'area':'Marketing','finding':f'{high} costs the most per reported conversion.', 'evidence':f"{format_currency(valid.loc[high, 'Cost per conversion'])} per reported result versus {format_currency(valid.loc[low, 'Cost per conversion'])} on {low}.", 'action':'Check what each reported conversion represents before testing a small budget change. The files do not show which orders came from each campaign.', 'basis':'Compares reported campaign results. It does not prove which campaign caused a sale.'})
    return result
