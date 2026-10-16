"""Order-time outcome classification with untouched chronological test data."""
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from vaultdata.ml.common import SEED, temporal_split, pipeline, classification_metrics, InsufficientData

NUMERIC=['Quantity','Unit price','discount_pct','hour','weekday','month']
CATEGORICAL=['Product line','Region','Channel','Payment']
FEATURES=NUMERIC+CATEGORICAL

def order_features(transactions):
    df=transactions.copy()
    time=pd.to_datetime(df.timestamp)
    df['hour']=time.dt.hour; df['weekday']=time.dt.dayofweek; df['month']=time.dt.month
    return df

def evaluate_order_risk(transactions,outcome_delay_days=30):
    if outcome_delay_days<0:
        raise ValueError('The assumed outcome delay must be nonnegative.')
    frame=order_features(transactions)
    # No actual resolution timestamps are supplied. Use a documented conservative
    # maturation assumption instead of allowing outcomes at the cutoff boundary.
    frame['assumed_outcome_available']=pd.to_datetime(frame.timestamp).dt.normalize()+pd.Timedelta(days=outcome_delay_days)
    resolved=frame[frame.Status.isin(['Completed','Cancelled','Returned'])]
    train,val,test,split=temporal_split(resolved,'timestamp',label_time='assumed_outcome_available')
    split['assumed_outcome_maturation_days']=outcome_delay_days
    if train.Status.nunique()<3:
        raise InsufficientData('Training history must contain completed, cancelled, and returned orders.')
    candidates={
        'prior_baseline':pipeline(DummyClassifier(strategy='prior'),NUMERIC,CATEGORICAL),
        'logistic_regression':pipeline(LogisticRegression(max_iter=1000,random_state=SEED),NUMERIC,CATEGORICAL),
        'gradient_boosting':pipeline(HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=10,l2_regularization=10,early_stopping=False,random_state=SEED),NUMERIC,CATEGORICAL),
    }
    validation={}
    for name,model in candidates.items():
        model.fit(train[FEATURES],train.Status)
        validation[name]=classification_metrics(val.Status,model.predict_proba(val[FEATURES]),model.classes_)
    selected=min(validation,key=lambda name:validation[name]['log_loss'])
    # No test rows are used in tuning or model selection. Refit only train+validation.
    fit=pd.concat([train,val])
    selected_model=clone(candidates[selected]).fit(fit[FEATURES],fit.Status)
    baseline=clone(candidates['prior_baseline']).fit(fit[FEATURES],fit.Status)
    probabilities=selected_model.predict_proba(test[FEATURES])
    test_metrics=classification_metrics(test.Status,probabilities,selected_model.classes_)
    baseline_metrics=classification_metrics(test.Status,baseline.predict_proba(test[FEATURES]),baseline.classes_)
    # Non-selected test candidate comparisons are deliberately omitted to keep test use diagnostic only.
    importance=[]
    if selected!='prior_baseline':
        diagnostic=permutation_importance(selected_model,test[FEATURES],test.Status,scoring='neg_log_loss',n_repeats=3,random_state=SEED,n_jobs=1)
        importance=[{'feature':f,'log_loss_increase':float(v)} for f,v in sorted(zip(FEATURES,diagnostic.importances_mean),key=lambda pair:pair[1],reverse=True)]
    rows=test[['Invoice ID','Date','Product line','Status']].copy()
    for i,cls in enumerate(selected_model.classes_): rows[f'probability_{cls.lower()}']=probabilities[:,i]
    # Deployment fit occurs only after the test evaluation is finalized.
    deployed=clone(candidates[selected]).fit(resolved[FEATURES],resolved.Status)
    pending=frame[frame.Status=='Pending'].copy()
    if len(pending):
        p=deployed.predict_proba(pending[FEATURES])
        pending['cancellation_or_return_probability']=1-p[:,list(deployed.classes_).index('Completed')]
    summary={
        'task':'Predict Completed, Cancelled, or Returned using order-time attributes; Pending outcomes excluded from fitting.',
        'selected_model':selected,'selection_metric':'lowest validation log loss','seed':SEED,
        'features':FEATURES,'excluded_features':['Status (target)','customer_id','product_id','Customer type (profile timing unknown)','signup_date (inconsistent dates)','Total','Estimated margin','future inventory','campaign conversions'],
        'split':split,'resolved_rows':len(resolved),'pending_rows':len(pending),'validation':validation,'test':test_metrics,'test_baseline':baseline_metrics,
        'test_log_loss_improvement':baseline_metrics['log_loss']-test_metrics['log_loss'],
        'supports_individual_ranking':selected!='prior_baseline' and test_metrics['log_loss']<baseline_metrics['log_loss'],
        'feature_importance':importance,
        'limitations':['Synthetic outcomes may have no learnable signal. A baseline may be the best validated choice.', f'Outcome resolution timestamps are unavailable. A {outcome_delay_days}-day assumed maturation window purges near-boundary outcomes; this is not proof of actual availability. Operational deployment needs measured resolution timestamps.', 'Regions and product categories are assumed available at order creation. Customer profile groups are excluded because their historical timing is unknown.', 'Pending-order estimates are current-snapshot deployment scores fitted after test evaluation; they are not predictions recorded at their historical order times.', 'Probabilities are estimates, not explanations or proof that a particular order will fail.']}
    return summary,rows,pending
