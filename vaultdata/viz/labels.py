"""Plain-language display labels; calculations keep their original field names."""
STOCK_LABELS = {'Stockout signal':'Reported out of stock','Reorder':'Running low','Healthy':'Above restock level'}
COLUMN_LABELS = {
    'Signal':'Stock status','product_id':'Product','category':'Category','date':'Date',
    'stock_on_hand':'Units left','reorder_threshold':'Restock at or below',
    'supplier_lead_days':'Supplier delivery (days)','supplier_delay_days':'Recorded delay (days)',
    'Product line':'Category','Customer type':'Customer group','Affected value':'Cancelled + returned value',
    'Fallout rate %':'Cancelled + returned (%)','Completed discounts':'Discounts on completed orders',
    'Completed revenue':'Revenue from completed orders','spend':'Spend','impressions':'Ad views',
    'clicks':'Clicks','conversions':'Reported conversions','CTR %':'Ad views that led to clicks (%)',
    'Conversion rate %':'Clicks that led to conversions (%)','Cost per conversion':'Cost per reported conversion',
    'customer_id':'Customer ID','customer_segment':'Customer group','signup_date':'Signup date',
    'preferred_channel':'Preferred shopping channel','transaction_id':'Order ID','timestamp':'Order date and time',
    'quantity':'Units','unit_price':'Selling price per unit','discount_pct':'Discount (fraction of price)',
    'status':'Order status','channel':'Channel','payment_method':'Payment method',
    'unit_cost':'Cost per unit','list_price':'Listed price','inventory_record_id':'Stock record ID',
    'stockout_flag':'Marked out of stock (1 = yes)','campaign_id':'Campaign ID','region':'Region',
    'Avg Transaction Value':'Average order value','Revenue Share %':'Share of revenue (%)',
    'Invoice ID':'Order ID','Quantity':'Units','Unit price':'Selling price per unit','Total':'Order value after discount',
    'Gross value':'Order value before discount','Discount value':'Discount amount','cogs':'Recorded product cost',
    'Estimated margin':'Order value minus recorded product cost','net order value':'Order value after discount',
}

def readable_table(df):
    result = df.copy()
    if 'Signal' in result:
        result['Signal'] = result.Signal.map(STOCK_LABELS).fillna(result.Signal)
    result = result.rename(columns=COLUMN_LABELS)
    if result.index.name in COLUMN_LABELS:
        result.index.name = COLUMN_LABELS[result.index.name]
    return result
