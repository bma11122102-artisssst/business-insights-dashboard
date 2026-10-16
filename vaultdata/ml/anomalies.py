"""Retrospective daily anomaly detection; no fraud labels or invented accuracy."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from vaultdata.ml.common import SEED,InsufficientData

FEATURES=['completed_revenue','orders','cancel_rate','return_rate','average_discount','units_sold']

def daily_features(transactions):
    dates=pd.date_range(transactions.Date.min(),transactions.Date.max(),freq='D')
    d=transactions.copy()
    d['completed_revenue']=np.where(d.Status=='Completed',d.Total,0)
    d['units_sold']=np.where(d.Status=='Completed',d.Quantity,0)
    d['cancel_rate']=(d.Status=='Cancelled').astype(float)
    d['return_rate']=(d.Status=='Returned').astype(float)
    result=d.groupby('Date').agg(completed_revenue=('completed_revenue','sum'),orders=('Invoice ID','size'),cancel_rate=('cancel_rate','mean'),return_rate=('return_rate','mean'),average_discount=('discount_pct','mean'),units_sold=('units_sold','sum'))
    return result.reindex(dates,fill_value=0)

def detect_anomalies(transactions):
    daily=daily_features(transactions)
    if len(daily)<60: raise InsufficientData('At least 60 days are required to separate earlier history from later checks.')
    cutoff=int(len(daily)*.8);train=daily.iloc[:cutoff];test=daily.iloc[cutoff:]
    model=IsolationForest(n_estimators=150,contamination=.05,random_state=SEED,n_jobs=1).fit(train[FEATURES])
    score=-model.score_samples(test[FEATURES]); flags=model.predict(test[FEATURES])==-1
    medians=train.median();scale=(train.quantile(.75)-train.quantile(.25)).replace(0,1.)
    deviation=(test-medians)/scale
    names={'completed_revenue':'sales revenue','orders':'order count','cancel_rate':'cancellation rate','return_rate':'return rate','average_discount':'average discount','units_sold':'items sold'}
    rows=test.copy(); rows['Date']=test.index;rows['unusual']=flags;rows['unusualness_score']=score
    reasons=[]
    for _,values in deviation.iterrows():
        fields=values.abs().nlargest(2).index
        reasons.append('; '.join(f"{names[f]} {'higher' if values[f]>0 else 'lower'} than the earlier middle value" for f in fields))
    rows['what_to_check']=reasons
    summary={'method':'IsolationForest','seed':SEED,'features':FEATURES,'training_days':len(train),'training_end':str(train.index[-1].date()),'test_start':str(test.index[0].date()),'test_days':len(test),'flagged_days':int(flags.sum()),'assumed_training_contamination':.05,
        'performance_status':'No labeled anomalies exist; precision, recall, and anomaly accuracy cannot be measured.',
        'limitations':['Flags are unusual historical patterns, not fraud findings or predictions of future problems.', 'Training uses the earliest 80% of days. Later days are scored without refitting.', 'Explanations compare observed metrics with training medians and IQR; they are descriptive, not causal explanations of the model.']}
    return summary,rows.sort_values('unusualness_score',ascending=False).reset_index(drop=True)
