from dataclasses import replace
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from vaultdata.data.track4 import load_sources, prepare_transactions, completed, is_track4
from vaultdata.analytics.leakage import summarize, stock_snapshot, campaign_metrics, findings
from vaultdata.components.filters import FilterState, apply_filters

@pytest.fixture(scope='module')
def sources():
    return load_sources()

@pytest.fixture(scope='module')
def transactions(sources):
    return prepare_transactions(sources)

def test_all_five_sources_and_validated_join(sources, transactions):
    assert sum(map(len,sources.values())) == 27450
    assert len(transactions) == 18000
    assert transactions['Invoice ID'].is_unique
    assert transactions[['customer_id','product_id','Product line','Region']].notna().all().all()
    assert is_track4(transactions)

def test_revenue_uses_completed_transaction_prices(sources, transactions):
    raw = sources['transactions']
    expected = (raw.quantity * raw.unit_price * (1-raw.discount_pct))[raw.status=='Completed'].sum()
    assert completed(transactions).Total.sum() == pytest.approx(expected)
    grouped = summarize(transactions, 'Product line')
    assert grouped['Completed revenue'].sum() == pytest.approx(expected)
    assert grouped['Affected value'].sum() == pytest.approx(transactions.loc[transactions.Status.isin(['Cancelled','Returned']),'Total'].sum())

def test_filter_scope_and_snapshot(sources, transactions):
    state = FilterState(date_range=('2025-03-01','2025-03-31'),product_lines=['Beauty'],regions=['West'],channels=['App'])
    tx = apply_filters(transactions,state)
    assert set(tx.Region)=={'West'} and set(tx.Channel)=={'App'}
    stock = stock_snapshot(sources['inventory'],sources['products'],state)
    assert stock.product_id.is_unique and set(stock.category)=={'Beauty'}
    assert stock.date.between('2025-03-01','2025-03-31').all()
    pd.testing.assert_frame_equal(stock,stock_snapshot(sources['inventory'],sources['products'],replace(state,regions=['East'],channels=['Store'])))
    campaign = campaign_metrics(sources['campaigns'],state)
    assert list(campaign.index)==['App']

def test_stock_rule_priority_and_latest_date(sources):
    inv = sources['inventory'].iloc[:3].copy()
    inv['product_id'] = sources['products'].iloc[0].product_id
    inv['date'] = ['2025-01-01','2025-01-02','2025-01-03']
    inv['stock_on_hand'] = [100,0,5];inv['reorder_threshold']=10;inv['stockout_flag']=0
    stock = stock_snapshot(inv,sources['products'],FilterState())
    assert len(stock)==1 and stock.iloc[0].Signal=='Reorder' and stock.iloc[0].stock_on_hand==5
    inv.loc[2,'stockout_flag']=1
    assert stock_snapshot(inv,sources['products'],FilterState()).iloc[0].Signal=='Stockout signal'

def test_empty_support_and_no_findings(sources, transactions):
    state=FilterState(date_range=('2024-01-01','2024-01-02'))
    stock=stock_snapshot(sources['inventory'],sources['products'],state)
    campaign=campaign_metrics(sources['campaigns'],state)
    assert stock.empty and campaign.empty
    assert findings(transactions.iloc[:0],stock,campaign)==[]

@pytest.mark.parametrize('view',['executive_overview','sales_intelligence','customer_intelligence','inventory_intelligence','campaign_intelligence','forecasting','recommendations','data_explorer','about'])
def test_original_streamlit_pages_support_track4(view):
    script=f'''
import streamlit as st
from vaultdata.data.track4 import load_sources, prepare_transactions
from vaultdata.components.filters import FilterState, FILTER_STATE_KEY
from views import {view}
df=prepare_transactions(load_sources())
st.session_state[FILTER_STATE_KEY]=FilterState(date_range=('2025-01-01','2025-12-31'))
{view}.render(df,df)
'''
    app=AppTest.from_string(script).run(timeout=60)
    assert not app.exception, [e.message for e in app.exception]

def test_dataset_switch_and_reset():
    app=AppTest.from_file(Path(__file__).resolve().parents[1] / 'streamlit_app.py').run(timeout=60)
    assert not app.exception
    app.multiselect(key='filter_Region').select('West').run()
    assert app.multiselect(key='filter_Region').value == ['West']
    next(b for b in app.button if b.label=='Reset filters').click().run()
    assert app.multiselect(key='filter_Region').value == []
    app.selectbox(key='data_source').select('Original supermarket demo').run()
    assert not app.exception
    assert any(m.label=='Avg Customer Rating' for m in app.metric)
