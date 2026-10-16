"""Conversion-count diagnostic model with explicit feature timing and exclusions."""
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import PoissonRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from vaultdata.ml.common import SEED,temporal_split,pipeline,regression_metrics,InsufficientData

NUMERIC=['spend','impressions','clicks','weekday','month']
CATEGORICAL=['channel','category']
FEATURES=NUMERIC+CATEGORICAL

def valid_campaigns(campaigns):
    valid=(campaigns.clicks>0)&(campaigns.clicks<=campaigns.impressions)&(campaigns.conversions<=campaigns.clicks)
    frame=campaigns.loc[valid].copy();frame['date']=pd.to_datetime(frame.date)
    frame['weekday']=frame.date.dt.dayofweek;frame['month']=frame.date.dt.month
    return frame,int((~valid).sum())

def evaluate_campaigns(campaigns):
    frame,excluded=valid_campaigns(campaigns)
    train,val,test,split=temporal_split(frame,'date')
    baseline_rate=train.conversions.sum()/train.clicks.sum()
    candidates={
        'poisson_regression':pipeline(PoissonRegressor(alpha=1,max_iter=1000),NUMERIC,CATEGORICAL),
        'gradient_boosting':pipeline(HistGradientBoostingRegressor(loss='poisson',max_iter=100,max_leaf_nodes=7,l2_regularization=20,early_stopping=False,random_state=SEED),NUMERIC,CATEGORICAL),
    }
    validation={'click_rate_baseline':regression_metrics(val.conversions,val.clicks*baseline_rate)}
    for name,model in candidates.items():
        model.fit(train[FEATURES],train.conversions)
        validation[name]=regression_metrics(val.conversions,np.clip(model.predict(val[FEATURES]),0,val.clicks.to_numpy()))
    selected=min(validation,key=lambda name:validation[name]['mae'])
    fit=pd.concat([train,val]);rate=fit.conversions.sum()/fit.clicks.sum()
    baseline=test.clicks.to_numpy()*rate
    if selected=='click_rate_baseline':prediction=baseline
    else:
        model=clone(candidates[selected]).fit(fit[FEATURES],fit.conversions)
        prediction=np.clip(model.predict(test[FEATURES]),0,test.clicks.to_numpy())
    rows=test[['campaign_id','date','channel','category','spend','clicks','conversions']].copy()
    rows['expected_conversions']=prediction;rows['click_rate_baseline']=baseline;rows['actual_minus_expected']=rows.conversions-prediction
    summary={'task':'Expected reported conversion count given measured campaign spend, impressions, clicks, date, channel, and category.',
        'prediction_time':'After engagement counts are available; diagnostic benchmark, not a pre-launch forecast.',
        'selected_model':selected,'selection_metric':'lowest validation MAE','features':FEATURES,
        'excluded_features':['conversions (target)','conversion rate','cost per conversion','campaign_id','transaction revenue'],
        'excluded_invalid_count_rows':excluded,'eligible_rows':len(frame),'split':split,'validation':validation,
        'output_constraint':'0 <= expected conversions <= measured clicks, matching the explicitly chosen count-chain cohort.',
        'test':regression_metrics(test.conversions,prediction),'test_baseline':regression_metrics(test.conversions,baseline),
        'limitations':['Rows with clicks exceeding impressions, conversions exceeding clicks, or zero clicks are excluded from modeling but retained in raw data analysis.', 'Conversions are reported counts, not unique customers or attributable orders.', 'Inputs contain measured clicks, so this model must not be presented as predicting conversions before a campaign runs.', 'Synthetic campaigns may contain little learnable structure. A click-rate baseline is a legitimate selected model.']}
    return summary,rows
