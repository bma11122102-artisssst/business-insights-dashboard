"""Shared evaluation utilities. No preprocessing is fitted before splitting."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import log_loss, f1_score, balanced_accuracy_score, confusion_matrix, roc_auc_score, average_precision_score, mean_absolute_error, mean_squared_error

SEED=42

class InsufficientData(ValueError):
    pass

def temporal_split(df,time_col, label_time=None):
    dates=pd.to_datetime(df[time_col]).dt.normalize()
    days=np.sort(dates.unique())
    if len(days)<30 or len(df)<100:
        raise InsufficientData('At least 30 distinct days and 100 rows are needed for a chronological evaluation.')
    val_start=pd.Timestamp(days[int(len(days)*.6)])
    test_start=pd.Timestamp(days[int(len(days)*.8)])
    train=dates<val_start; val=(dates>=val_start)&(dates<test_start); test=dates>=test_start
    if label_time:
        labels=pd.to_datetime(df[label_time])
        train &= labels<val_start
        val &= labels<test_start
    parts=[df.loc[mask].copy() for mask in [train,val,test]]
    if min(map(len,parts))<20:
        raise InsufficientData('Too few rows remain after chronological label-availability checks.')
    info={'method':'chronological 60/20/20 by unique feature date; whole days never overlap', 'validation_start':str(val_start.date()),'test_start':str(test_start.date()),'excluded_boundary_rows':len(df)-sum(map(len,parts)),
          'partitions':{name:{'rows':len(part),'start':str(pd.to_datetime(part[time_col]).min()),'end':str(pd.to_datetime(part[time_col]).max())} for name,part in zip(['train','validation','test'],parts)}}
    if label_time:
        info['label_availability_rule']='Every training label date is strictly before validation starts; every validation label date is strictly before test starts.'
    return (*parts,info)

def pipeline(estimator,numeric,categorical):
    preprocessing=ColumnTransformer([
        ('numeric',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),numeric),
        ('categorical',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical),
    ],remainder='drop')
    return Pipeline([('features',preprocessing),('model',estimator)])

def classification_metrics(y,probabilities,classes):
    y=np.asarray(y); p=np.asarray(probabilities); classes=np.asarray(classes)
    prediction=classes[p.argmax(axis=1)]
    result={'log_loss':float(log_loss(y,p,labels=classes)), 'macro_f1':float(f1_score(y,prediction,labels=classes,average='macro',zero_division=0)),
            'balanced_accuracy':float(balanced_accuracy_score(y,prediction)), 'confusion_matrix':confusion_matrix(y,prediction,labels=classes).tolist(),'class_order':classes.tolist()}
    positive = (y!= 'Completed').astype(int) if 'Completed' in classes else y.astype(int)
    risk = 1-p[:,list(classes).index('Completed')] if 'Completed' in classes else p[:,list(classes).index(1)]
    result['risk_brier']=float(np.mean((positive-risk)**2))
    result['risk_roc_auc']=float(roc_auc_score(positive,risk)) if len(np.unique(positive))==2 else None
    result['risk_average_precision']=float(average_precision_score(positive,risk)) if positive.any() else None
    return result

def regression_metrics(actual,prediction):
    y=np.asarray(actual,dtype=float); p=np.asarray(prediction,dtype=float)
    denominator=np.abs(y).sum()
    return {'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))), 'wape_pct':float(100*np.abs(y-p).sum()/denominator) if denominator else None}

def finite_json(value):
    """Convert numpy/date scalars and replace nonfinite diagnostics with null."""
    if isinstance(value,dict): return {str(k):finite_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)): return [finite_json(v) for v in value]
    if isinstance(value,(np.integer,)): return int(value)
    if isinstance(value,(float,np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value,(pd.Timestamp,np.datetime64)): return str(value)
    if isinstance(value,(np.bool_,)): return bool(value)
    return value
