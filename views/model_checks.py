"""Visible, evidence-backed model results; never retrain on each dashboard rerun."""
import json
import pandas as pd
import streamlit as st
from vaultdata.config import REPO_ROOT
from vaultdata.data.track4 import is_track4,TRACK4_PATH
from vaultdata.data.audit import report_matches_sources

REPORTS=REPO_ROOT/'reports'

@st.cache_data(show_spinner=False)
def read_report(signature):
    return json.loads((REPORTS/'evaluation.json').read_text(encoding='utf-8'))

def render(df_filtered,df_all):
    st.header('Model checks')
    if not is_track4(df_all):
        st.info('Choose the Track 4 files to see model results. These checks do not apply to the original demo or uploaded files.')
        return
    path=REPORTS/'evaluation.json'
    if not path.exists():
        st.info('Run the offline checks first: python -m vaultdata.ml.evaluate --output reports')
        return
    report=read_report(path.stat().st_mtime_ns);models=report['models']
    if not report_matches_sources(report,TRACK4_PATH):
        st.warning('The data changed after these checks were saved. Run python -m vaultdata.ml.evaluate --output reports to update them.')
        return
    st.info('These checks use the complete official files, not the sidebar filters. Models are tested on later dates that were kept out of training and model selection. Results describe this sample, not guaranteed future business performance.')
    tabs=st.tabs(['Order outcomes','Stock','Items sold','Customer groups','Unusual days','Marketing','File checks'])
    with tabs[0]:
        r=models['order_outcomes'];st.subheader('Can we predict cancellations and returns?')
        show_classification(r)
        if not r['supports_individual_ranking']:
            st.warning('This sample did not establish a useful improvement over the overall past outcome rates. Individual orders should not be treated as high or low risk based on this model.')
        st.write('Pending orders are excluded from training because their outcomes are not known.')
        st.write('The pending estimates below are made from the current file snapshot after evaluation. They are not predictions recorded on the original order dates.')
        display_csv('pending_order_estimates.csv','Pending orders with estimated overall risk',limit=100)
    with tabs[1]:
        r=models['stock_next_record'];st.subheader('Will the next stock record report a shortage?')
        show_classification(r)
        st.info(f"Stock records are not taken at regular intervals. The middle gap is {r['observation_gap_days']['median']:.0f} days. This estimates the next recorded state, not a shortage within a fixed number of days.")
        if not r['supports_individual_ranking']:
            st.warning('The stock model did not establish useful individual ranking. Use recorded stock levels and check conflicting records before deciding what to order.')
        display_csv('stock_latest_estimates.csv','Latest-record estimates',limit=100)
    with tabs[2]:
        st.subheader('How closely can we estimate items sold?')
        rows=[]
        for category,r in models['daily_units'].items():
            rows.append({'Category':category,'Chosen method':r['selected_model'],'Average daily error (items)':r['test']['mae'],'Simple weekly baseline error':r['test_baseline']['mae'],'Share within estimated range':r['test']['interval_coverage_80']})
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.write('Methods are chosen using two earlier 14-day checks. The table measures the final 14 days, which were not used to choose a method. A simple recent average is kept when it works best.')
        st.info('These estimates cover recorded completed sales. Demand lost while a product was unavailable is not observed. The ranges are approximate; their measured coverage is shown rather than assumed.')
        display_csv('daily_units_forecasts.csv','Next 30-day estimates',limit=60)
    with tabs[3]:
        r=models['customer_groups'];st.subheader('Groups based on actual purchase histories')
        a,b,c=st.columns(3);a.metric('Customers grouped',r['customers_clustered']);b.metric('Groups found',r['selected_k']);c.metric('Group separation score',f"{r['silhouette']:.3f}")
        st.dataframe(pd.DataFrame(r['groups']).rename(columns={'mean_recency_days':'Average days since purchase','mean_completed_orders':'Average completed orders','mean_spend':'Average spending','customers':'Customers','revenue':'Revenue (₹)','group':'Group'}),hide_index=True,width='stretch')
        st.info('These groups use time since last purchase, purchase count, and spending. The separation score measures how distinct the groups are; it is not an accuracy percentage or a prediction of customer behavior.')
    with tabs[4]:
        r=models['unusual_days'];st.subheader('Days worth checking')
        st.write(f"{r['flagged_days']} of {r['test_days']} later days were unusual compared with earlier sales patterns.")
        st.info('There are no confirmed unusual-day labels in the files, so we cannot claim detection accuracy. A flag is a reason to inspect records, not proof of fraud or a business failure.')
        rows=pd.read_csv(REPORTS/'unusual_days.csv');st.dataframe(rows[rows.unusual].head(30),hide_index=True,width='stretch')
        st.download_button('Download unusual-day checks',(REPORTS/'unusual_days.csv').read_bytes(),'unusual_days.csv','text/csv')
    with tabs[5]:
        r=models['campaign_conversions'];st.subheader('Expected campaign results after clicks are known')
        a,b=st.columns(2);a.metric('Average error in conversion count',f"{r['test']['mae']:.1f}");b.metric('Simple baseline error',f"{r['test_baseline']['mae']:.1f}")
        st.write(f"Chosen method: {r['selected_model']}. {r['excluded_invalid_count_rows']} invalid or zero-click rows were excluded from model training and remain available in the original-file view.")
        st.info('The model uses measured clicks and ad views, so it is a check on already measured campaigns, not a forecast before launch. It cannot connect campaigns to revenue or individual purchases.')
        display_csv('campaign_holdout_predictions.csv','Results on later campaign records',limit=100)
    with tabs[6]:
        audit=report['audit'];st.subheader('Checks across all five files')
        st.dataframe(pd.DataFrame([{'File':name+'.csv','Rows':row['rows'],'Missing values':row['missing_cells'],'Repeated IDs':not row['primary_key_unique']} for name,row in audit['tables'].items()]),hide_index=True,width='stretch')
        st.dataframe(pd.DataFrame(audit['issues']).rename(columns={'check':'Check','count':'Records','handling':'How handled'}),hide_index=True,width='stretch')
        st.write('Raw source files have not been changed. Checksums, features, date cutoffs, model-selection results, and output files are recorded in the downloadable report.')
    st.download_button('Download full evaluation report',path.read_bytes(),'evaluation.json','application/json')
    if 'external_benchmark' in report:
        with st.expander('External retail demand benchmark'):
            from vaultdata.ml.external import EXTERNAL_PATH
            import hashlib
            r=report['external_benchmark']
            if hashlib.sha256((EXTERNAL_PATH/'daily_sales.csv').read_bytes()).hexdigest()!=r['source_sha256']:
                st.warning('The external file changed. Rebuild evaluation before using these results.')
            else:
                st.write('A separate model is fitted on UCI Online Retail daily item sales. It is not combined with the challenge business or used to claim that its model transfers to another business.')
                a,b=st.columns(2)
                a.metric('Average daily error (items)',f"{r['test']['mae']:.1f}")
                b.metric('Simple weekly baseline error',f"{r['test_baseline']['mae']:.1f}")
                st.write(f"Chosen method: {r['selected_model']}. Source: Daqing Chen, UCI Online Retail, CC BY 4.0.")
                st.json({k:r[k] for k in ['scope','split','test','test_baseline','limitations'] if k in r})
                display_csv('external_units_holdout.csv','External retail later-date predictions')
    with st.expander('Reproduce the checks'):
        st.code('python -m vaultdata.ml.evaluate --output reports\npython -m pytest -q',language='bash')
        st.write(report['environment'])

def show_classification(result):
    a,b,c=st.columns(3)
    a.metric('Probability error (lower is better)',f"{result['test']['log_loss']:.4f}")
    b.metric('Simple baseline error',f"{result['test_baseline']['log_loss']:.4f}")
    auc=result['test']['risk_roc_auc'];c.metric('Ranking score (0.5 is chance)',f'{auc:.3f}' if auc is not None else 'Unavailable')
    st.write(f"Chosen method: {result['selected_model']}. Selection uses an earlier validation period; the displayed errors use a separate later test period.")
    with st.expander('Dates, features, and detailed checks'):
        st.json({key:result[key] for key in ['features','split','validation','test','test_baseline','limitations']})

def display_csv(name,title,limit=100):
    path=REPORTS/name
    st.markdown(f'**{title}**')
    st.dataframe(pd.read_csv(path).head(limit),hide_index=True,width='stretch')
    st.download_button('Download '+title.lower(),path.read_bytes(),name,'text/csv',key='download_'+name)
