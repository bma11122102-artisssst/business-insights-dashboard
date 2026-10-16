"""Interactive quantity forecasting backed by the same offline evaluator."""
import streamlit as st
from vaultdata.ml.demand import daily_series,evaluate_series
from vaultdata.ml.common import InsufficientData
from vaultdata.components.filters import FILTER_STATE_KEY
from vaultdata.viz.charts import forecast_chart

@st.cache_data(show_spinner=False)
def cached_forecast(df,category,start,end,horizon):
    series=daily_series(df,'Quantity',category,start,end)
    return evaluate_series(series,future_days=horizon)

def render(df):
    st.subheader('How many items might sell?')
    if df.empty:
        st.info('No orders match these filters.');return
    category=st.selectbox('Category to estimate',['All categories']+sorted(df['Product line'].unique()))
    horizon=st.select_slider('Days ahead',options=[7,14,30,60],value=14)
    state=st.session_state.get(FILTER_STATE_KEY)
    bounds=state.date_range if state and state.date_range else (df.Date.min(),df.Date.max())
    try:
        with st.spinner('Checking earlier estimates and comparing simple methods…'):
            result,future,holdout=cached_forecast(df,None if category=='All categories' else category,*bounds,horizon)
    except InsufficientData as exc:
        st.info(str(exc));return
    historical=daily_series(df,'Quantity',None if category=='All categories' else category,*bounds)
    f=future.set_index('Date')
    fig=forecast_chart(historical,f.Estimate,f.Lower,f.Upper,'Estimated items sold')
    fig.update_yaxes(title='Items')
    fig.update_traces(hovertemplate='%{x|%d %b %Y}<br>%{y:,.1f} items<extra>%{fullData.name}</extra>')
    st.plotly_chart(fig,width='stretch')
    a,b,c=st.columns(3);a.metric('Estimated items over chosen days',f'{future.Estimate.sum():,.0f}');b.metric('Average daily error on held-out days',f"{result['test']['mae']:.1f} items");c.metric('Simple weekly baseline error',f"{result['test_baseline']['mae']:.1f} items")
    st.info(f"Chosen method: {result['selected_model']}. We compare two earlier 14-day checks, then measure errors on a separate final 14 days. Estimates describe recorded sales, not demand we missed during stock shortages. The 80% range is approximate; coverage on those final days was {result['test']['interval_coverage_80']:.0%}.")
    st.dataframe(future,hide_index=True,width='stretch')
    st.download_button('Download item estimates',future.to_csv(index=False),'unit_forecast.csv','text/csv')
