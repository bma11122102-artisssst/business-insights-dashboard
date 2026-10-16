"""Run offline: python -m vaultdata.ml.evaluate --output reports"""
import argparse
from datetime import datetime,timezone
from importlib.metadata import version
from pathlib import Path
import json
import hashlib
import platform
from vaultdata.data.track4 import load_sources,prepare_transactions,TRACK4_PATH
from vaultdata.data.audit import audit_sources
from vaultdata.ml.common import SEED,finite_json
from vaultdata.ml.order_risk import evaluate_order_risk
from vaultdata.ml.stock_risk import evaluate_stock_risk
from vaultdata.ml.demand import daily_series,evaluate_series
from vaultdata.ml.customers import segment_customers
from vaultdata.ml.anomalies import detect_anomalies
from vaultdata.ml.campaigns import evaluate_campaigns
from vaultdata.ml.external import evaluate_external
from vaultdata.analytics.leakage import stock_snapshot,campaign_metrics
from vaultdata.analytics.restocking import restock_plan
from vaultdata.analytics.action_plan import build_action_plan
from vaultdata.components.filters import FilterState

def write_csv(frame,path):
    frame.to_csv(path,index=False,lineterminator='\n')

def run_evaluation(output='reports',source_path=TRACK4_PATH):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    sources=load_sources(Path(source_path));transactions=prepare_transactions(sources)
    report={'schema_version':1,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'random_seed':SEED,
        'source':'Official DATATHON Track 4 synthetic business files. Raw files unchanged.',
        'environment':{'python':platform.python_version(),**{name:version(name) for name in ['pandas','numpy','scikit-learn','statsmodels','streamlit']}},
        'audit':audit_sources(sources,source_path),'models':{},'artifacts':[],'artifact_sha256':{}}
    def save(name,frame):
        write_csv(frame,output/name);report['artifacts'].append(name)
        report['artifact_sha256'][name]=hashlib.sha256((output/name).read_bytes()).hexdigest()
    print('Evaluating order outcomes...',flush=True)
    summary,holdout,pending=evaluate_order_risk(transactions);report['models']['order_outcomes']=summary
    save('order_holdout_predictions.csv',holdout)
    save('pending_order_estimates.csv',pending[['Invoice ID','Date','Product line','cancellation_or_return_probability']])
    print('Evaluating next-record stock risk...',flush=True)
    summary,holdout,latest=evaluate_stock_risk(sources);report['models']['stock_next_record']=summary
    save('stock_holdout_predictions.csv',holdout);save('stock_latest_estimates.csv',latest)
    print('Backtesting daily units and revenue...',flush=True)
    demand={};future=[];checks=[]
    for category in [None]+sorted(transactions['Product line'].unique()):
        key='All categories' if category is None else category
        summary,forecast,holdout=evaluate_series(daily_series(transactions,'Quantity',category),future_days=30)
        demand[key]=summary;forecast['Category']=key;holdout['Category']=key
        future.append(forecast);checks.append(holdout)
    import pandas as pd
    report['models']['daily_units']=demand
    save('daily_units_forecasts.csv',pd.concat(future,ignore_index=True));save('daily_units_holdout.csv',pd.concat(checks,ignore_index=True))
    summary,forecast,holdout=evaluate_series(daily_series(transactions,'Total'),future_days=30)
    report['models']['daily_revenue']=summary;save('revenue_forecast.csv',forecast);save('revenue_holdout.csv',holdout)
    print('Building customer groups and checking unusual days...',flush=True)
    summary,assignments=segment_customers(transactions);report['models']['customer_groups']=summary;save('customer_groups.csv',assignments)
    profile=transactions.assign(preferred_channel_match=lambda d:(d.Channel==d.preferred_channel).astype(float)).groupby('customer_id').agg(recorded_orders=('Invoice ID','size'),preferred_channel_match_rate=('preferred_channel_match','mean'))
    profile=sources['customers'].merge(profile,on='customer_id',how='left',validate='one_to_one')
    save('customer_profile_context.csv',profile)
    report['customer_profile_context']={'rows':len(profile),'file':'customer_profile_context.csv','interpretation':'Supplied region, segment, signup, and preferred channel describe the customer-file snapshot. Preferred-channel match is descriptive; signup inconsistencies are audited separately.'}
    summary,anomalies=detect_anomalies(transactions);report['models']['unusual_days']=summary;save('unusual_days.csv',anomalies)
    print('Evaluating campaign conversions...',flush=True)
    summary,predictions=evaluate_campaigns(sources['campaigns']);report['models']['campaign_conversions']=summary;save('campaign_holdout_predictions.csv',predictions)
    state=FilterState(date_range=(transactions.Date.min(),transactions.Date.max()))
    stock=stock_snapshot(sources['inventory'],sources['products'],state);campaigns=campaign_metrics(sources['campaigns'],state)
    plan=restock_plan(transactions,stock)
    save('restock_scenario.csv',plan)
    report['restock_policy']={'method':'order-up-to scenario using 30-day observed completed units, supplier lead plus recorded delay, 7-day review, safety multiplier 1.28',
        'formula':'trigger = mean * lead + z * std * sqrt(lead); target = ceil(mean * (lead + review) + z * std * sqrt(lead + review)); quantity=max(0,target-stock) only at/below trigger',
        'blocked_records':int(plan['Suggested units'].isna().sum()),'limitations':['Not mathematically optimal inventory. Missing holding costs, ordering costs, open purchase orders, uncensored demand, and true stock movements prevent validated optimization.', 'Flag/quantity conflicts and stock records older than 14 days (or future-dated) block quantity suggestions pending verification.', 'Safety multiplier and normal-demand approximation are user assumptions, not an empirically established service guarantee.']}
    report['action_plan']=build_action_plan(transactions,stock,campaigns)
    # Context only: aggregate each side BEFORE joining; never attribute sales to campaigns.
    sales=transactions.groupby(['Date','Product line','Channel']).agg(completed_revenue=('Total',lambda s:float(s[transactions.loc[s.index,'Status']=='Completed'].sum())),orders=('Invoice ID','size')).reset_index().rename(columns={'Date':'date','Product line':'category','Channel':'channel'})
    camp=sources['campaigns'].assign(date=lambda d:pd.to_datetime(d.date)).groupby(['date','category','channel'])[['spend','clicks','conversions']].sum().reset_index()
    context=camp.merge(sales,on=['date','category','channel'],how='left',validate='one_to_one')
    context['interpretation']='Shared date/category/channel context only; no attributed campaign revenue or ROAS.'
    save('campaign_sales_context.csv',context)
    print('Evaluating separate external retail demand benchmark...',flush=True)
    summary,forecast,holdout=evaluate_external()
    report['external_benchmark']=summary
    save('external_units_forecast.csv',forecast)
    save('external_units_holdout.csv',holdout)
    report=finite_json(report)
    temporary=output/'evaluation.json.tmp'
    temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(output/'evaluation.json')
    write_summary(report,output/'EVALUATION.md')
    print(f'Wrote {output / "evaluation.json"} and {len(report["artifacts"])} CSV artifacts.',flush=True)
    return report

def write_summary(report,path):
    m=report['models'];lines=['# Track 4 — Reproducible evaluation','',f"Generated: {report['generated_at_utc']}",'','Track 4 results below are measured on the supplied synthetic files; the external benchmark is identified separately. Model selection uses validation data; final test data is reserved for evaluation. No cloud key or language-model request is used.','', '## Supervised results','', '| Task | Validation-selected method | Test error | Baseline error | Interpretation |','|---|---|---:|---:|---|']
    for key,label,error in [('order_outcomes','Order outcomes','log_loss'),('stock_next_record','Next recorded stock state','log_loss'),('campaign_conversions','Campaign conversion counts','mae'),('daily_revenue','Daily completed revenue','mae')]:
        result=m[key];measured=result['test'][error];baseline=result['test_baseline'][error]
        interpretation='Baseline retained; no individual predictive lift established.' if 'baseline' in result['selected_model'] else 'Held-out improvement observed.' if measured<baseline else 'No held-out improvement; do not assume operational lift.'
        lines.append(f"| {label} | {result['selected_model']} | {measured:.6f} ({error}) | {baseline:.6f} | {interpretation} |")
    lines+=['','## Daily unit forecasts','','| Category | Selected method | Test MAE (units/day) | Seasonal baseline MAE | 80% range coverage |','|---|---|---:|---:|---:|']
    for category,r in m['daily_units'].items():
        lines.append(f"| {category} | {r['selected_model']} | {r['test']['mae']:.3f} | {r['test_baseline']['mae']:.3f} | {r['test']['interval_coverage_80']:.1%} |")
    group=m['customer_groups'];anomaly=m['unusual_days']
    lines+=['','## Unsupervised diagnostics','',f"- Customer KMeans: {group['customers_clustered']} customers; k={group['selected_k']}; silhouette={group['silhouette']:.4f}; Davies–Bouldin={group['davies_bouldin']:.4f}. These measure separation, not prediction accuracy.",f"- IsolationForest: {anomaly['flagged_days']} flagged of {anomaly['test_days']} later days. No anomaly ground truth exists; precision/recall cannot be claimed.",'','## Data audit','','| Check | Count | Handling |','|---|---:|---|']
    for issue in report['audit']['issues']: lines.append(f"| {issue['check']} | {issue['count']} | {issue['handling']} |")
    ext=report.get('external_benchmark')
    if ext:
        lines+=['','## Separate external retail benchmark','',
                'UCI Online Retail, Daqing Chen (2015), CC BY 4.0, DOI: 10.24432/C5BW33. Customer-free daily aggregates; never pooled with Track 4.',
                f"Independently fitted daily-unit method: {ext['selected_model']}; test MAE {ext['test']['mae']:.3f} items versus weekly baseline {ext['test_baseline']['mae']:.3f}. Measured approximate 80% range coverage: {ext['test']['interval_coverage_80']:.1%}.",
                f"Final test: {ext['test_start']} to {ext['test_end']}. This is a separate fit, not proof that the Track 4 model transfers to another business."]
    lines+=['','## Reproduce','','```powershell','python -m vaultdata.ml.evaluate --output reports','python -m pytest -q','```','','See `evaluation.json` for exact features, dates, model-selection scores, confusion matrices, exclusions, seeds, environment versions, and dataset SHA-256 hashes. CSV files contain held-out predictions, future forecasts, customer assignments, and observed evidence.','', '## Limits','','Synthetic data does not establish real-world generalization. Stock horizons are irregular; campaign models use measured clicks; sales forecasts estimate observed completed sales; missing operational records prevent causal savings claims or validated inventory optimization. Rupee display is a presentation assumption, not currency conversion.']
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='reports');parser.add_argument('--data',default=str(TRACK4_PATH));args=parser.parse_args()
    run_evaluation(args.output,Path(args.data))

if __name__=='__main__': main()
