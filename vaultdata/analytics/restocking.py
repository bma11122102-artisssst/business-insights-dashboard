"""Explainable restock scenarios, not claimed optimal orders or guaranteed savings."""
import numpy as np
import pandas as pd

def restock_plan(transactions,stock,review_days=7,safety_factor=1.28,budget=None):
    if review_days<1 or safety_factor<0 or (budget is not None and budget<0):
        raise ValueError('Review days must be positive; safety and budget must be nonnegative.')
    if transactions.empty or stock.empty: return pd.DataFrame()
    as_of=transactions.Date.max()
    daily=transactions[(transactions.Status=='Completed') & transactions.Date.between(as_of-pd.Timedelta(days=29),as_of)].groupby(['product_id','Date']).Quantity.sum()
    days=pd.date_range(as_of-pd.Timedelta(days=29),as_of,freq='D')
    rows=[]
    for _,row in stock.iterrows():
        history=daily.loc[row.product_id].reindex(days,fill_value=0) if row.product_id in daily.index.get_level_values(0) else pd.Series(0.,index=days)
        mean=float(history.mean());std=float(history.std(ddof=0))
        lead=float(row.supplier_lead_days+row.supplier_delay_days)
        trigger=mean*lead+safety_factor*std*np.sqrt(lead)
        target=int(np.ceil(mean*(lead+review_days)+safety_factor*std*np.sqrt(lead+review_days)))
        conflict=bool(row.stockout_flag==1 and row.stock_on_hand>0)
        age=int((as_of-pd.Timestamp(row.date)).days)
        quantity=max(0,target-int(row.stock_on_hand)) if row.stock_on_hand<=trigger else 0
        # A conflicting, future, or stale record must be verified before using a quantity.
        blocked=conflict or age<0 or age>14
        rows.append({'Product':row.product_id,'Category':row.category,'Units left':int(row.stock_on_hand),'Last updated':row.date,
            'Stock record age (days)':age,'Average daily sales (30d)':mean,'Daily sales variation':std,'Days to receive stock':lead,
            'Planning restock level':float(trigger),'Planning target units':target,'Suggested units':None if blocked else quantity,
            'Recorded unit cost':float(row.unit_cost),'Illustrative cost':None if blocked else quantity*row.unit_cost,
            'Check needed':'Verify conflicting stock record' if conflict else 'Verify old or future stock record' if blocked else 'Review suggested quantity',
            '_priority':row.stock_on_hand/max(mean,.01)})
    plan=pd.DataFrame(rows).sort_values('_priority').drop(columns='_priority').reset_index(drop=True)
    if budget is not None:
        remaining=float(budget);allocated=[]
        for _,row in plan.iterrows():
            if pd.isna(row['Suggested units']): allocated.append(None);continue
            cost=row['Recorded unit cost'];desired=int(row['Suggested units'])
            count=min(desired,int(remaining//cost)) if cost>0 else 0
            allocated.append(count);remaining-=count*cost
        plan['Units within example budget']=allocated
    return plan
