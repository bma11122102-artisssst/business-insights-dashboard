from pathlib import Path
from xml.etree import ElementTree
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from vaultdata.viz.formatting import format_currency,compact_currency,rupee_table
from vaultdata.viz.charts import revenue_trend_chart,distribution_donut
from vaultdata.config import LOGO_PATH

@pytest.mark.parametrize('value,expected',[(7301698.249,'₹73,01,698.25'),(123456.78,'₹1,23,456.78'),(0,'₹0.00'),(-1234.5,'-₹1,234.50'),(None,'N/A')])
def test_rupee_formatting(value,expected):
    assert format_currency(value)==expected

def test_quantity_columns_stay_numeric_and_money_style_does_not_change_values():
    frame=pd.DataFrame({'Revenue':[123456.78],'Orders':[12],'Units':[35]})
    styled=rupee_table(frame)
    pd.testing.assert_frame_equal(frame,styled.data)
    html=styled.to_html()
    assert '₹1,23,456.78' in html and '₹35' not in html
    assert compact_currency(7301698).startswith('₹73.02 L')

def test_charts_label_money_as_rupees():
    series=pd.Series([120,140],index=pd.date_range('2025-01-01',periods=2))
    chart=revenue_trend_chart(series)
    assert '₹' in chart.layout.yaxis.title.text
    assert '₹' in chart.data[0].hovertemplate
    pie=distribution_donut(pd.Series({'Web':120}), 'Spend','rupees',money=True)
    assert '₹' in pie.data[0].hovertemplate

def test_overview_sales_metrics_are_first_and_completed_only():
    script='''
import streamlit as st
from vaultdata.data.track4 import load_sources,prepare_transactions
from vaultdata.components.filters import FilterState,FILTER_STATE_KEY
from views.executive_overview import render
df=prepare_transactions(load_sources())
st.session_state[FILTER_STATE_KEY]=FilterState(date_range=('2025-01-01','2025-12-31'))
render(df,df)
'''
    app=AppTest.from_string(script).run(timeout=30)
    assert not app.exception
    assert [m.label for m in app.metric[:4]]==['Sales revenue','Completed orders','Items sold','Average order value']
    metrics={m.label:m.value for m in app.metric}
    assert metrics['Sales revenue']=='₹73,01,698'
    assert metrics['Completed orders']=='13,962'
    assert metrics['Items sold']=='42,097'
    assert metrics['Marketing spend']=='₹48,05,016'

def test_logo_asset_is_valid_svg_and_app_loads():
    assert ElementTree.parse(LOGO_PATH).getroot().tag.endswith('svg')
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'streamlit_app.py').run(timeout=30)
    assert not app.exception
    assert len(app.get('image'))==1
