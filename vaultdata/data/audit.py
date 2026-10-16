"""Track 4 data contracts and non-destructive consistency checks."""
from pathlib import Path
import hashlib
import pandas as pd
from vaultdata.data.loader import DataLoadError

CONTRACTS = {
    'customers': ('customer_id', ['customer_id','region','customer_segment','signup_date','preferred_channel']),
    'products': ('product_id', ['product_id','category','unit_cost','list_price','supplier_lead_days']),
    'transactions': ('transaction_id', ['transaction_id','customer_id','product_id','timestamp','quantity','unit_price','discount_pct','status','channel','payment_method']),
    'inventory': ('inventory_record_id', ['inventory_record_id','product_id','date','stock_on_hand','reorder_threshold','stockout_flag','supplier_delay_days']),
    'campaigns': ('campaign_id', ['campaign_id','date','channel','category','spend','impressions','clicks','conversions']),
}

def validate_sources(sources):
    """Reject broken structural contracts; preserve imperfect but analyzable samples."""
    for name,(key,columns) in CONTRACTS.items():
        if name not in sources:
            raise DataLoadError(f'Missing Track 4 file: {name}.csv')
        frame=sources[name]
        missing=set(columns)-set(frame.columns)
        if missing:
            raise DataLoadError(f'{name}.csv is missing required columns: {sorted(missing)}')
        if frame.empty or frame[key].isna().any() or frame[key].duplicated().any():
            raise DataLoadError(f'{name}.csv must have nonempty, unique {key} values.')
        if frame[columns].isna().any().any():
            raise DataLoadError(f'{name}.csv contains missing required values.')
    for table,column,parent in [('transactions','customer_id','customers'),('transactions','product_id','products'),('inventory','product_id','products')]:
        if not sources[table][column].isin(sources[parent][column]).all():
            raise DataLoadError(f'{table}.csv has unknown {column} references.')
    numeric={
        'products':['unit_cost','list_price','supplier_lead_days'],
        'transactions':['quantity','unit_price','discount_pct'],
        'inventory':['stock_on_hand','reorder_threshold','stockout_flag','supplier_delay_days'],
        'campaigns':['spend','impressions','clicks','conversions'],
    }
    for name,columns in numeric.items():
        for col in columns:
            if not pd.api.types.is_numeric_dtype(sources[name][col]):
                raise DataLoadError(f'{name}.{col} must be a numeric column.')
            values=pd.to_numeric(sources[name][col],errors='coerce')
            if values.isna().any() or not values.map(lambda x: float('-inf') < x < float('inf')).all() or (values<0).any():
                raise DataLoadError(f'{name}.{col} must contain finite, nonnegative numbers.')
    t=sources['transactions']; i=sources['inventory']
    if not t.discount_pct.between(0,1).all() or (t.quantity<=0).any():
        raise DataLoadError('Transactions require positive quantities and discounts between 0 and 1.')
    if not t.status.isin(['Completed','Cancelled','Returned','Pending']).all() or not i.stockout_flag.isin([0,1]).all():
        raise DataLoadError('Unknown order status or invalid stockout flag.')
    for name,col in [('transactions','timestamp'),('customers','signup_date'),('inventory','date'),('campaigns','date')]:
        if pd.to_datetime(sources[name][col],format='ISO8601',errors='coerce').isna().any():
            raise DataLoadError(f'{name}.{col} contains invalid dates.')

def audit_sources(sources, path=None):
    validate_sources(sources)
    tables={}
    for name,(key,_) in CONTRACTS.items():
        d=sources[name]
        tables[name]={'rows':len(d),'columns':list(d.columns),'missing_cells':int(d.isna().sum().sum()),'duplicate_rows':int(d.duplicated().sum()),'primary_key':key,'primary_key_unique':bool(d[key].is_unique)}
        if path:
            tables[name]['sha256']=hashlib.sha256((Path(path)/f'{name}.csv').read_bytes()).hexdigest()
    joined=sources['transactions'].merge(sources['customers'],on='customer_id').merge(sources['products'],on='product_id')
    inv=sources['inventory']; c=sources['campaigns']
    checks=[
        ('orders_before_customer_signup',int((pd.to_datetime(joined.timestamp)<pd.to_datetime(joined.signup_date)).sum()),'Keep orders for sales totals; exclude signup-derived features from order prediction.'),
        ('stock_flag_with_positive_units',int(((inv.stockout_flag==1)&(inv.stock_on_hand>0)).sum()),'Show the conflict. Do not silently overwrite stock or claim a verified physical stockout.'),
        ('campaign_conversions_above_clicks',int((c.conversions>c.clicks).sum()),'Keep raw analysis visible; exclude impossible count chains from campaign model training.'),
        ('campaign_clicks_above_impressions',int((c.clicks>c.impressions).sum()),'Keep raw analysis visible; exclude impossible count chains from campaign model training.'),
        ('completed_orders_below_recorded_cost',int(((joined.status=='Completed') & (joined.unit_price*(1-joined.discount_pct)<joined.unit_cost)).sum()),'Costs and prices are independently generated; no audited profit or savings claims.'),
        ('duplicate_product_inventory_dates',int(inv.duplicated(['product_id','date']).sum()),'For next-observation modeling keep the last record ID on a product/date; record the exclusion count.'),
    ]
    return {'tables':tables,'total_rows':sum(len(d) for d in sources.values()),'structural_contracts_passed':True,'issues':[{'check':k,'count':n,'handling':h} for k,n,h in checks],
        'source_url':'https://datathon-xi.vercel.app/problem-statements.html#track-4','raw_files_modified':False}


def report_matches_sources(report,path):
    try:
        return all(report['audit']['tables'][name]['sha256']==hashlib.sha256((Path(path)/f'{name}.csv').read_bytes()).hexdigest() for name in CONTRACTS)
    except (OSError,KeyError,TypeError):
        return False
