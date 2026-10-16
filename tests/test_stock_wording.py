from streamlit.testing.v1 import AppTest
import pandas as pd
from vaultdata.viz.labels import readable_table

SCRIPT='''
import streamlit as st
from vaultdata.data.track4 import load_sources,prepare_transactions
from vaultdata.components.filters import FILTER_STATE_KEY,FilterState
from views.inventory_intelligence import render
s=load_sources(); df=prepare_transactions(s)
st.session_state[FILTER_STATE_KEY]=FilterState()
render(df,df)
'''

def test_plain_labels_preserve_stock_values_and_flags():
    original=pd.DataFrame({'product_id':['A','B','C'],'Signal':['Stockout signal','Reorder','Healthy'],'stock_on_hand':[7,10,90],'reorder_threshold':[5,10,20]})
    display=readable_table(original)
    assert list(display['Stock status'])==['Reported out of stock','Running low','Above restock level']
    assert list(display['Units left'])==[7,10,90]
    assert list(display['Restock at or below'])==[5,10,20]
    assert original.Signal.iloc[0]=='Stockout signal'

def test_stock_page_replaces_comparison_chart_with_plain_list():
    app=AppTest.from_string(SCRIPT).run(timeout=30)
    assert not app.exception
    assert len(app.get('plotly_chart'))==1  # status donut only; no bar/diamond comparison
    table=app.dataframe[0].value
    assert {'Units left','Restock at or below','Last updated','Stock status'}.issubset(table.columns)
    text=' '.join(x.value for x in app.caption)+ ' '.join(x.value for x in app.markdown)
    assert 'stock signal' not in text.lower() and 'threshold' not in text.lower()
    counts=table['Stock status'].value_counts()
    app.multiselect(key='stock_status').select('Running low').run(timeout=30)
    assert not app.exception
    filtered=app.dataframe[0].value
    assert len(filtered)==counts.get('Running low',0)
    assert set(filtered['Stock status'])=={'Running low'}
