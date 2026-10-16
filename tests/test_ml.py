from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from vaultdata.data.track4 import load_sources,prepare_transactions,TRACK4_PATH
from vaultdata.data.audit import validate_sources,audit_sources
from vaultdata.data.loader import DataLoadError
from vaultdata.ml.common import temporal_split,InsufficientData
from vaultdata.ml.order_risk import evaluate_order_risk,FEATURES as ORDER_FEATURES
from vaultdata.ml.stock_risk import stock_features,evaluate_stock_risk,FEATURES as STOCK_FEATURES
from vaultdata.ml.demand import daily_series,evaluate_series,predict_series
from vaultdata.ml.customers import customer_features,segment_customers
from vaultdata.ml.anomalies import detect_anomalies
from vaultdata.ml.campaigns import valid_campaigns,evaluate_campaigns,FEATURES as CAMPAIGN_FEATURES
from vaultdata.analytics.restocking import restock_plan
from vaultdata.analytics.action_plan import build_action_plan
from vaultdata.analytics.leakage import stock_snapshot,campaign_metrics
from vaultdata.components.filters import FilterState

@pytest.fixture(scope='module')
def sources(): return load_sources()

@pytest.fixture(scope='module')
def transactions(sources): return prepare_transactions(sources)

def test_audit_finds_cross_file_contradictions_without_changing_rows(sources):
    before={name:df.copy(deep=True) for name,df in sources.items()}
    report=audit_sources(sources)
    checks={row['check']:row['count'] for row in report['issues']}
    assert report['total_rows']==27450
    assert checks['orders_before_customer_signup']==797
    assert checks['stock_flag_with_positive_units']==760
    assert checks['campaign_conversions_above_clicks']==88
    assert checks['campaign_clicks_above_impressions']==84
    for name in sources: pd.testing.assert_frame_equal(sources[name],before[name])

@pytest.mark.parametrize('problem',['missing_column','duplicate_id','unknown_product','bad_discount','unknown_status','negative_cost','invalid_date'])
def test_contracts_reject_structural_errors(sources,problem):
    changed={n:d.copy() for n,d in sources.items()}
    if problem=='missing_column': changed['inventory']=changed['inventory'].drop(columns='stock_on_hand')
    elif problem=='duplicate_id': changed['products'].loc[1,'product_id']=changed['products'].loc[0,'product_id']
    elif problem=='unknown_product': changed['transactions'].loc[0,'product_id']='MISSING'
    elif problem=='bad_discount': changed['transactions'].loc[0,'discount_pct']=2.
    elif problem=='unknown_status': changed['transactions'].loc[0,'status']='Imaginary'
    elif problem=='negative_cost': changed['products'].loc[0,'unit_cost']=-1.
    elif problem=='invalid_date': changed['inventory'].loc[0,'date']='not a date'
    with pytest.raises(DataLoadError): validate_sources(changed)

def test_chronological_split_purges_labels_crossing_boundaries():
    d=pd.DataFrame({'date':pd.date_range('2025-01-01',periods=150),'label_date':pd.date_range('2025-01-04',periods=150)})
    train,val,test,report=temporal_split(d,'date','label_date')
    assert train.date.max()<val.date.min()<test.date.min()
    assert train.label_date.max()<pd.Timestamp(report['validation_start'])
    assert val.label_date.max()<pd.Timestamp(report['test_start'])
    assert report['excluded_boundary_rows']==6
    assert not set(train.date)&set(val.date) and not set(val.date)&set(test.date)

def test_order_model_selection_excludes_pending_and_target_features(transactions):
    summary,holdout,pending=evaluate_order_risk(transactions)
    assert summary['pending_rows']==918 and summary['resolved_rows']==17082
    assert summary['split']['assumed_outcome_maturation_days']==30
    assert summary['split']['excluded_boundary_rows']>0
    assert not {'Status','customer_id','product_id','Estimated margin','signup_date'}&set(ORDER_FEATURES)
    assert summary['selected_model']==min(summary['validation'],key=lambda n:summary['validation'][n]['log_loss'])
    assert holdout.Status.isin(['Completed','Cancelled','Returned']).all()
    np.testing.assert_allclose(holdout.filter(like='probability_').sum(axis=1),1.)
    assert pending.cancellation_or_return_probability.between(0,1).all()
    if summary['selected_model']=='prior_baseline':
        assert not summary['supports_individual_ranking']
        assert summary['test']['log_loss']==pytest.approx(summary['test_baseline']['log_loss'])
        assert pending.cancellation_or_return_probability.nunique()==1

def test_stock_inputs_do_not_use_future_order_quantities(sources):
    original,_=stock_features(sources)
    modified={n:d.copy() for n,d in sources.items()};cutoff=pd.Timestamp('2025-06-01')
    later=pd.to_datetime(modified['transactions'].timestamp)>=cutoff
    modified['transactions'].loc[later,'quantity']*=1000
    changed,_=stock_features(modified)
    columns=['ordered_units_prior_7d','ordered_units_prior_30d']
    pd.testing.assert_frame_equal(original.loc[original.date<cutoff,columns],changed.loc[changed.date<cutoff,columns])
    assert not {'target','stockout_flag','next_flag','next_stock','next_date'}&set(STOCK_FEATURES)

def test_stock_evaluation_labels_are_future_and_purged(sources):
    summary,holdout,latest=evaluate_stock_risk(sources)
    assert summary['split']['excluded_boundary_rows']>0
    assert summary['duplicate_product_dates_collapsed']==114
    assert (holdout.next_date>holdout.date).all()
    assert holdout.next_record_stockout_probability.between(0,1).all()
    assert latest.product_id.is_unique
    if summary['selected_model']=='prior_baseline': assert not summary['supports_individual_ranking']

def test_forecast_test_values_cannot_change_model_choice_or_calibration():
    rng=np.random.default_rng(42)
    series=pd.Series(np.maximum(0,20+rng.normal(0,2,120)),index=pd.date_range('2025-01-01',periods=120))
    a,_,_=evaluate_series(series)
    changed=series.copy();changed.iloc[-14:]=1_000_000
    b,_,_=evaluate_series(changed)
    assert a['selected_model']==b['selected_model']
    assert a['validation']==b['validation']
    assert a['test']['mae']!=b['test']['mae']
    for window in a['validation_windows']:
        assert window['training_end']<window['validation_start']<=window['validation_end']<a['test_start']

def test_daily_unit_series_fills_absent_days_and_excludes_unresolved_orders():
    df=pd.DataFrame({'Date':pd.to_datetime(['2025-01-01','2025-01-03','2025-01-03']),'Status':['Completed','Completed','Pending'],'Quantity':[2,3,90],'Product line':['A','A','A']})
    assert daily_series(df,'Quantity').tolist()==[2.,0.,3.]
    assert predict_series(pd.Series([1.,2.,3.,4.,5.,6.,7.]),9,'seasonal_naive').tolist()==[1,2,3,4,5,6,7,1,2]

def test_zero_sales_forecast_has_no_fabricated_demand_or_nan():
    series=pd.Series(0.,index=pd.date_range('2025-01-01',periods=120))
    report,future,_=evaluate_series(series)
    assert report['test']['mae']==0 and report['test']['wape_pct'] is None
    assert future[['Estimate','Lower','Upper']].eq(0).all().all()

def test_customer_snapshot_excludes_future_and_pending_purchases():
    df=pd.DataFrame({'customer_id':['A','A','A'],'Date':pd.to_datetime(['2025-01-01','2025-01-10','2025-01-02']),'Status':['Completed','Completed','Pending'],'Invoice ID':['1','2','3'],'Total':[50.,500.,999.]})
    profile=customer_features(df,as_of='2025-01-03')
    assert profile.loc['A'].to_dict()=={'recency':2.,'frequency':1.,'monetary':50.}

def test_customer_clusters_cover_actual_buyers_and_not_supplied_labels(transactions):
    summary,groups=segment_customers(transactions)
    assert len(groups)==transactions.loc[transactions.Status=='Completed','customer_id'].nunique()
    assert groups.customer_id.is_unique and 2<=summary['selected_k']<=6
    assert -1<=summary['silhouette']<=1
    assert summary['selected_k']==max(summary['candidate_silhouettes'],key=summary['candidate_silhouettes'].get)

def test_anomalies_are_scored_on_later_dates_without_accuracy_claim(transactions):
    summary,rows=detect_anomalies(transactions)
    assert rows.Date.min()>pd.Timestamp(summary['training_end'])
    assert rows.unusual.sum()==summary['flagged_days']
    assert np.isfinite(rows.unusualness_score).all()
    assert 'cannot be measured' in summary['performance_status']

def test_campaign_model_excludes_invalid_chains_and_target_ratios(sources):
    frame,excluded=valid_campaigns(sources['campaigns'])
    assert excluded==171 and len(frame)==1029
    assert (frame.conversions<=frame.clicks).all() and (frame.clicks<=frame.impressions).all()
    assert not {'conversions','Cost per conversion','Conversion rate %'}&set(CAMPAIGN_FEATURES)
    summary,rows=evaluate_campaigns(sources['campaigns'])
    assert rows.expected_conversions.ge(0).all()
    assert rows.expected_conversions.le(rows.clicks).all()
    assert summary['selected_model']==min(summary['validation'],key=lambda n:summary['validation'][n]['mae'])
    assert 'not a pre-launch forecast' in summary['prediction_time']

def test_restock_plan_blocks_unreliable_records_and_respects_budget():
    df=pd.DataFrame({'Date':list(pd.date_range('2025-12-02',periods=30))*3,'product_id':['A']*30+['B']*30+['C']*30,'Status':['Completed']*90,'Quantity':[2]*90})
    stock=pd.DataFrame({'product_id':['A','B','C'],'category':['Home']*3,'stock_on_hand':[0,5,0],'reorder_threshold':[10]*3,'stockout_flag':[0,1,0],'date':pd.to_datetime(['2025-12-31','2025-12-31','2025-11-01']),'supplier_lead_days':[5]*3,'supplier_delay_days':[0]*3,'unit_cost':[10.]*3})
    plan=restock_plan(df,stock,budget=25)
    assert plan.set_index('Product').loc['A','Suggested units']>0
    assert pd.isna(plan.set_index('Product').loc['B','Suggested units'])
    assert pd.isna(plan.set_index('Product').loc['C','Suggested units'])
    assert (plan['Units within example budget']*plan['Recorded unit cost']).sum()<=25

def test_step_by_step_engine_works_without_cloud(sources,transactions):
    state=FilterState();stock=stock_snapshot(sources['inventory'],sources['products'],state);campaigns=campaign_metrics(sources['campaigns'],state)
    tasks=build_action_plan(transactions,stock,campaigns)
    assert tasks and tasks[0]['id']=='stock-record-check'
    assert all(len(task['steps'])>=2 and task['supporting_numbers'] and task['track'] and task['limit'] for task in tasks)

def test_checked_in_evaluation_matches_source_hashes_and_artifacts():
    path=Path(__file__).resolve().parents[1]/'reports'
    report=json.loads((path/'evaluation.json').read_text(encoding='utf-8'))
    for name,table in report['audit']['tables'].items():
        assert table['sha256']==hashlib.sha256((TRACK4_PATH/f'{name}.csv').read_bytes()).hexdigest()
    assert all((path/name).is_file() for name in report['artifacts'])
    for name,digest in report['artifact_sha256'].items():
        assert hashlib.sha256((path/name).read_bytes()).hexdigest()==digest
    assert 'api_key' not in json.dumps(report).lower()

def test_model_checks_page_renders_without_cloud_calls():
    script='''
from vaultdata.data.track4 import load_sources,prepare_transactions
from views.model_checks import render
df=prepare_transactions(load_sources());render(df,df)
'''
    app=AppTest.from_string(script).run(timeout=30)
    assert not app.exception,[e.message for e in app.exception]
    assert any('not the sidebar filters' in item.value for item in app.info)

def test_units_forecast_ui_uses_items_not_rupees():
    script='''
from vaultdata.data.track4 import load_sources,prepare_transactions
from views.unit_forecast import render
render(prepare_transactions(load_sources()))
'''
    app=AppTest.from_string(script).run(timeout=30)
    assert not app.exception,[e.message for e in app.exception]
    assert any('items' in metric.value for metric in app.metric)
    assert not any('₹' in metric.value for metric in app.metric)

def test_stock_planning_button_builds_guarded_example():
    script='''
import streamlit as st
from vaultdata.data.track4 import load_sources,prepare_transactions
from vaultdata.components.filters import FilterState,FILTER_STATE_KEY
from views.inventory_intelligence import render
df=prepare_transactions(load_sources());st.session_state[FILTER_STATE_KEY]=FilterState()
render(df,df)
'''
    app=AppTest.from_string(script).run(timeout=30)
    next(button for button in app.button if button.label=='Build restock example').click().run(timeout=30)
    assert not app.exception,[e.message for e in app.exception]
    plan=next(item.value for item in app.dataframe if 'Suggested units' in item.value.columns)
    assert plan['Suggested units'].isna().any()
    assert 'Check needed' in plan.columns
