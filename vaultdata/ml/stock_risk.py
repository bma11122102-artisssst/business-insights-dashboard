"""Predict the NEXT recorded stock state, never the current record's own flag."""
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from vaultdata.ml.common import SEED,temporal_split,pipeline,classification_metrics,InsufficientData

NUMERIC=['stock_on_hand','reorder_threshold','supplier_delay_days','supplier_lead_days','previous_stock','days_since_previous','ordered_units_prior_7d','ordered_units_prior_30d','weekday','month']
CATEGORICAL=['category']
FEATURES=NUMERIC+CATEGORICAL

def stock_features(sources):
    original=sources['inventory'].copy()
    original['date']=pd.to_datetime(original.date)
    frame=original.sort_values(['product_id','date','inventory_record_id']).drop_duplicates(['product_id','date'],keep='last')
    excluded=len(original)-len(frame)
    frame=frame.merge(sources['products'],on='product_id',validate='many_to_one').sort_values(['product_id','date'])
    groups=frame.groupby('product_id',sort=False)
    frame['previous_stock']=groups.stock_on_hand.shift(1)
    frame['days_since_previous']=groups.date.diff().dt.days
    frame['next_date']=groups.date.shift(-1)
    frame['next_stock']=groups.stock_on_hand.shift(-1)
    frame['next_flag']=groups.stockout_flag.shift(-1)
    frame['target']=np.where(frame.next_date.notna(),((frame.next_flag==1)|(frame.next_stock<=0)).astype(float),np.nan)
    frame['weekday']=frame.date.dt.dayofweek; frame['month']=frame.date.dt.month
    # Only quantities booked before the record day, regardless of eventual order outcome.
    tx=sources['transactions'].copy();tx['time']=pd.to_datetime(tx.timestamp)
    tx_groups={pid:g.sort_values('time') for pid,g in tx.groupby('product_id')}
    frame['ordered_units_prior_7d']=0.;frame['ordered_units_prior_30d']=0.
    for pid,part in frame.groupby('product_id'):
        orders=tx_groups.get(pid)
        if orders is None: continue
        times=orders.time.to_numpy(dtype='datetime64[ns]'); totals=np.r_[0.,orders.quantity.to_numpy().cumsum()]
        dates=part.date.to_numpy(dtype='datetime64[ns]')
        right=np.searchsorted(times,dates,side='left')
        for days in [7,30]:
            left=np.searchsorted(times,dates-np.timedelta64(days,'D'),side='left')
            frame.loc[part.index,f'ordered_units_prior_{days}d']=totals[right]-totals[left]
    frame=frame.drop(columns=['next_stock','next_flag'])
    return frame,excluded

def evaluate_stock_risk(sources):
    frame,duplicates=stock_features(sources)
    labeled=frame[frame.target.notna()].copy();labeled['target']=labeled.target.astype(int)
    train,val,test,split=temporal_split(labeled,'date',label_time='next_date')
    if train.target.nunique()<2: raise InsufficientData('Stock training labels need both outcomes.')
    candidates={
        'prior_baseline':pipeline(DummyClassifier(strategy='prior'),NUMERIC,CATEGORICAL),
        'logistic_regression':pipeline(LogisticRegression(max_iter=1000,random_state=SEED),NUMERIC,CATEGORICAL),
        'gradient_boosting':pipeline(HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=7,l2_regularization=20,early_stopping=False,random_state=SEED),NUMERIC,CATEGORICAL),
    }
    validation={}
    for name,model in candidates.items():
        model.fit(train[FEATURES],train.target)
        validation[name]=classification_metrics(val.target,model.predict_proba(val[FEATURES]),model.classes_)
    selected=min(validation,key=lambda n:validation[n]['log_loss'])
    fit=pd.concat([train,val]);model=clone(candidates[selected]).fit(fit[FEATURES],fit.target)
    baseline=clone(candidates['prior_baseline']).fit(fit[FEATURES],fit.target)
    p=model.predict_proba(test[FEATURES])
    metrics=classification_metrics(test.target,p,model.classes_)
    baseline_metrics=classification_metrics(test.target,baseline.predict_proba(test[FEATURES]),baseline.classes_)
    predictions=test[['inventory_record_id','product_id','date','next_date','target']].copy()
    predictions['next_record_stockout_probability']=p[:,list(model.classes_).index(1)]
    final=clone(candidates[selected]).fit(labeled[FEATURES],labeled.target)
    latest=frame[frame.next_date.isna()].copy()
    latest['next_record_stockout_probability']=final.predict_proba(latest[FEATURES])[:,list(final.classes_).index(1)]
    latest=latest[['product_id','category','date','stock_on_hand','stockout_flag','next_record_stockout_probability']]
    gaps=(labeled.next_date-labeled.date).dt.days
    summary={'task':'Probability the next observation is flagged out of stock or has zero units; NOT a fixed-day forecast.',
        'selected_model':selected,'selection_metric':'lowest validation log loss','features':FEATURES,
        'excluded_features':['current stockout_flag','next stock quantity','next stockout flag','next observation date (split/label metadata only)','customer/region/campaign fields'],
        'split':split,'duplicate_product_dates_collapsed':duplicates,'labeled_rows':len(labeled),
        'observation_gap_days':{'median':float(gaps.median()),'mean':float(gaps.mean()),'max':int(gaps.max())},
        'validation':validation,'test':metrics,'test_baseline':baseline_metrics,
        'supports_individual_ranking':selected!='prior_baseline' and metrics['log_loss']<baseline_metrics['log_loss'],
        'limitations':['Stock observations are irregular. Next-record risk is not next-week risk.', 'Stockout flags contradict positive stock quantities in this sample. The target is a reported state, not verified physical availability.', 'Booked quantities before the observation date are known at order creation; final order status and future quantities are not features.', 'Boundary-crossing labels are purged so future stock labels cannot enter training or validation. No customer-region inventory relationship is assumed.']}
    return summary,predictions,latest
