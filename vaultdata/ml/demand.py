"""Unit/revenue forecasts with two rolling validation windows and a final holdout."""
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from vaultdata.ml.common import regression_metrics,InsufficientData

METHODS=('seasonal_naive','recent_mean','holt_winters')

def daily_series(transactions,value='Quantity',category=None,start=None,end=None):
    frame=transactions
    if category is not None: frame=frame[frame['Product line']==category]
    if transactions.empty: raise InsufficientData('No orders are available.')
    begin=pd.Timestamp(start) if start is not None else transactions.Date.min()
    finish=pd.Timestamp(end) if end is not None else transactions.Date.max()
    completed=frame[frame.Status=='Completed']
    index=pd.date_range(begin,finish,freq='D')
    return completed.groupby('Date')[value].sum().reindex(index,fill_value=0).astype(float)

def predict_series(history,horizon,method):
    values=np.asarray(history,dtype=float)
    if horizon<1 or len(values)<7: raise InsufficientData('Forecasting needs at least a week of history and a positive horizon.')
    if method=='seasonal_naive':
        forecast=np.resize(values[-7:],horizon)
    elif method=='recent_mean':
        forecast=np.repeat(np.mean(values[-28:]),horizon)
    elif method=='holt_winters':
        if len(values)<21: raise InsufficientData('Holt-Winters needs at least 21 days.')
        if np.ptp(values)<1e-10:
            return np.repeat(max(0.,values[-1]),horizon)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',category=UserWarning)
            fitted=ExponentialSmoothing(values,trend='add',seasonal='add',seasonal_periods=7,initialization_method='estimated').fit(optimized=True)
            forecast=fitted.forecast(horizon)
    else: raise ValueError(f'Unknown forecast method: {method}')
    return np.maximum(0,np.asarray(forecast,dtype=float))

def evaluate_series(series,horizon=14,future_days=30):
    series=series.astype(float)
    if len(series)<3*horizon+35 or not np.isfinite(series.to_numpy()).all() or (series<0).any():
        raise InsufficientData(f'At least {3*horizon+35} complete daily values are needed for forecast evaluation.')
    scores={};errors={};windows=[]
    # Last horizon days are untouched test; the two preceding blocks choose the model and range width.
    for method in METHODS:
        actuals=[];predictions=[]
        for fold,end in enumerate([len(series)-2*horizon,len(series)-horizon]):
            train=series.iloc[:end-horizon];actual=series.iloc[end-horizon:end]
            forecast=predict_series(train,horizon,method)
            actuals.extend(actual.tolist());predictions.extend(forecast.tolist())
            if method==METHODS[0]:windows.append({'training_end':str(train.index[-1].date()),'validation_start':str(actual.index[0].date()),'validation_end':str(actual.index[-1].date())})
        scores[method]=regression_metrics(actuals,predictions)
        errors[method]=np.asarray(actuals)-np.asarray(predictions)
    selected=min(scores,key=lambda name:scores[name]['mae'])
    history=series.iloc[:-horizon];actual=series.iloc[-horizon:]
    prediction=predict_series(history,horizon,selected)
    baseline=predict_series(history,horizon,'seasonal_naive')
    # Empirical absolute-error 80th percentile, calibrated on validation only.
    radius=float(np.quantile(np.abs(errors[selected]),.8,method='higher'))
    lower=np.maximum(0,prediction-radius);upper=prediction+radius
    metrics=regression_metrics(actual,prediction)
    metrics['interval_coverage_80']=float(np.mean((actual.to_numpy()>=lower)&(actual.to_numpy()<=upper)))
    metrics['mean_interval_width']=float(np.mean(upper-lower))
    future=predict_series(series,future_days,selected)
    forecast_frame=pd.DataFrame({'Date':pd.date_range(series.index[-1]+pd.Timedelta(days=1),periods=future_days,freq='D'),'Estimate':future,'Lower':np.maximum(0,future-radius),'Upper':future+radius})
    holdout=pd.DataFrame({'Date':actual.index,'Actual':actual.values,'Estimate':prediction,'Seasonal baseline':baseline,'Lower':lower,'Upper':upper})
    summary={'selected_model':selected,'selection_metric':'lowest MAE across two rolling validation blocks','validation':scores,'validation_windows':windows,
        'test_start':str(actual.index[0].date()),'test_end':str(actual.index[-1].date()),'test_days':horizon,
        'test':metrics,'test_baseline':regression_metrics(actual,baseline),'observed_days':len(series),
        'interval_method':'Validation-only absolute-error 80th percentile; pooled across forecast steps. Not a guaranteed coverage bound.',
        'limitations':['Forecasts estimate observed completed sales, not uncensored customer demand; missed sales during stockouts are not observed.', 'Only 28 calibration errors at default horizon. Interval width is held constant across future steps; long-horizon coverage is not validated.', 'Model choice uses validation MAE, never the final test. The seasonal naive baseline is always available.']}
    return summary,forecast_frame,holdout
