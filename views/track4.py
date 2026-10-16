"""Track-specific additions to the repository's existing Streamlit pages."""
import pandas as pd
import streamlit as st
import json
from dataclasses import replace
from vaultdata.components.filters import apply_filters
from vaultdata.analytics.action_plan import build_action_plan
from vaultdata.analytics.restocking import restock_plan
from vaultdata.analytics.leakage import filter_support
from vaultdata.data.audit import audit_sources
from vaultdata.ml.customers import segment_customers
from vaultdata.ml.common import InsufficientData
from vaultdata.analytics.leakage import summarize, stock_snapshot, campaign_metrics, findings
from vaultdata.components.filters import FILTER_STATE_KEY, FilterState
from vaultdata.components.state import track4_sources
from vaultdata.viz.charts import ranking_bar_chart, distribution_donut, outcome_trend_chart, campaign_funnel
from vaultdata.viz.labels import STOCK_LABELS, readable_table
from vaultdata.viz.formatting import format_currency, compact_currency, rupee_table

def supporting_data():
    sources = track4_sources()
    state = st.session_state.get(FILTER_STATE_KEY, FilterState())
    return stock_snapshot(sources['inventory'], sources['products'], state), campaign_metrics(sources['campaigns'], state)


@st.cache_data(show_spinner=False)
def cached_customer_groups(df):
    return segment_customers(df)

def leakage_summary(df):
    affected = df[df.Status.isin(['Cancelled','Returned'])]
    cancelled = df[df.Status == 'Cancelled']
    returned = df[df.Status == 'Returned']
    cols = st.columns(4)
    cols[0].metric('Cancelled order value', format_currency(cancelled.Total.sum()))
    cols[1].metric('Returned order value', format_currency(returned.Total.sum()))
    cols[2].metric('Orders cancelled or returned', f'{100*len(affected)/len(df):.1f}%' if len(df) else 'N/A')
    cols[3].metric('Pending orders', f'{int((df.Status == "Pending").sum()):,}')
    st.caption('Order values include discounts. Cancelled and returned order values show sales that did not stay completed; they do not tell us the actual money lost or refunded. Pending orders are counted separately.')

def investigation(df):
    st.subheader('Investigate cancellations & returns')
    leakage_summary(df)
    if df.empty:
        st.info('No transactions match this selection.')
        return
    dimension = st.selectbox('Compare by', ['Product line','Region','Channel','Customer type'], format_func=lambda x: {'Product line':'Category','Customer type':'Customer group'}.get(x,x))
    ranked = summarize(df, dimension)
    a,b = st.columns([1.2,1])
    with a:
        label = {'Product line':'category','Customer type':'customer group'}.get(dimension,dimension.lower())
        st.plotly_chart(ranking_bar_chart(ranked, 'Affected value', f'Cancelled + returned value by {label}', 'Order value'), width='stretch')
    with b:
        st.dataframe(df.groupby('Status').agg(Orders=('Total','size'), **{'Order value after discounts':('Total','sum')}), width='stretch')
    st.dataframe(rupee_table(readable_table(ranked)), width='stretch')
    st.plotly_chart(outcome_trend_chart(df), width='stretch')
    with st.expander('Why is this flagged?'):
        st.write('Categories with the highest value of cancelled or returned orders appear first. The percentage shows how many orders were cancelled or returned out of all orders in that group. Check the order count too: a percentage based on only a few orders can be misleading. The files do not tell us why an order was cancelled or returned.')

def overview_additions(df):
    st.subheader('Orders and stock at a glance')
    stock, campaigns = supporting_data()
    left,right = st.columns(2)
    with left:
        with st.container(border=True):
            st.plotly_chart(distribution_donut(df.Status.value_counts(),'Every order has an outcome','orders'),width='stretch')
            rate = float((df.Status == 'Completed').mean()) if len(df) else 0
            st.caption(f'Completed orders · {rate:.1%} of this selection')
            if len(df):
                st.caption(f"{df.Status.isin(['Cancelled','Returned']).mean():.1%} cancelled or returned · {int((df.Status=='Pending').sum()):,} pending orders")
            st.progress(rate)
    with right:
        with st.container(border=True):
            done = df[df.Status == 'Completed']
            counts = stock.Signal.map(STOCK_LABELS).value_counts()
            st.plotly_chart(distribution_donut(counts,'Products that may need restocking','products'),width='stretch')
            healthy = float((stock.Signal == 'Healthy').mean()) if len(stock) else 0
            st.caption(f'Products above their restock level · {healthy:.1%}' if len(stock) else 'No stock records for these dates and categories')
            st.progress(healthy)
    st.subheader('Where to investigate next')
    signals = findings(df, stock, campaigns)
    if signals:
        columns = st.columns(len(signals))
        for column,signal in zip(columns,signals):
            with column, st.container(border=True):
                st.caption(signal['area'].upper())
                st.markdown(f"**{signal['finding']}**")
                st.write(signal['evidence'])
                st.caption(signal['basis'])
    st.caption('Open Recommendations, choose your main goal, and ask LeakLens what to do next.')
    st.caption('Stock uses date and category filters. Marketing also uses the channel filter. Neither file has customer region or payment details.')

def inventory(df, df_all):
    st.header('Stock')
    st.caption('See which products are running low and check their latest recorded stock.')
    st.info('This page uses the date and category filters. The stock files do not contain region, customer group, payment method, or shopping channel. We show the latest record for each product within your chosen dates, not live stock levels.')
    stock, _ = supporting_data()
    if stock.empty:
        st.info('No stock records match these dates and categories.')
        return
    a,b,c = st.columns(3)
    a.metric('Products with stock records', len(stock))
    b.metric('Reported out of stock', int((stock.Signal == 'Stockout signal').sum()))
    c.metric('Running low', int((stock.Signal == 'Reorder').sum()))
    left,right = st.columns(2)
    with left:
        counts = stock.Signal.map(STOCK_LABELS).value_counts()
        st.plotly_chart(distribution_donut(counts,'Which products need attention?','products'), width='stretch')
    with right:
        st.subheader('What the stock labels mean')
        st.markdown('**Reported out of stock** — the latest record says the product is out of stock, or shows no units left.')
        st.markdown('**Running low** — some units are left, but the amount has reached the product’s restock level.')
        st.markdown('**Above restock level** — the recorded amount is above that level. This does not guarantee enough stock for future demand.')
        st.caption('Check the “Last updated” date and confirm current stock before ordering more. A record marked out of stock may still list units left; check that mismatch with your team.')
    st.subheader('Products to check')
    signal = st.multiselect('Show stock status', list(STOCK_LABELS.values()), default=[], key='stock_status')
    search = st.text_input('Find product or category', key='stock_search')
    view = stock[stock.Signal.map(STOCK_LABELS).isin(signal)] if signal else stock
    if search:
        view = view[view.product_id.str.contains(search, case=False, regex=False) | view.category.str.contains(search, case=False, regex=False)]
    columns = ['product_id','category','date','stock_on_hand','reorder_threshold','supplier_lead_days','supplier_delay_days','Signal']
    view = view.assign(_priority=view.Signal.map({'Stockout signal':0,'Reorder':1,'Healthy':2})).sort_values(['_priority','stock_on_hand'])
    display = readable_table(view[columns]).rename(columns={'Date':'Last updated'})
    st.dataframe(display, width='stretch', hide_index=True)
    st.download_button('Download stock list', display.to_csv(index=False), 'track4_stock_review.csv', 'text/csv')
    st.caption('Products reported out of stock appear first, followed by those running low. “Restock at or below” is the number of units at which the supplied data says to consider restocking. Delivery times and delays are recorded values, not promises.')
    with st.expander('Plan a restock'):
        st.info('This is an example plan, not a purchase order. It uses recent completed sales, recorded supplier delays, and extra stock for changing sales. Conflicting records, records over 14 days old, and future-dated records need checking before a quantity can be suggested. Supplier orders already on the way are not supplied in these files.')
        a,b,c=st.columns(3)
        review=a.number_input('Days between stock reviews',min_value=1,max_value=30,value=7)
        buffer=b.selectbox('Extra stock allowance',['Small','Standard','Larger'],index=1)
        budget=c.number_input('Example budget (₹; 0 means no cap)',min_value=0.,value=0.,step=1000.)
        if st.button('Build restock example',disabled=df.empty):
            state=st.session_state.get(FILTER_STATE_KEY,FilterState())
            planning_orders=apply_filters(df_all,replace(state,regions=[],channels=[],payments=[],customer_types=[],genders=[],branches=[]))
            plan=restock_plan(planning_orders,stock,review_days=review,safety_factor={'Small':1.,'Standard':1.28,'Larger':1.65}[buffer],budget=budget if budget>0 else None)
            st.dataframe(plan,hide_index=True,width='stretch')
            st.download_button('Download restock example',plan.to_csv(index=False),'restock_example.csv','text/csv')

def customers(df, df_all):
    st.header('Customers')
    st.caption('See who buys, who comes back, and how much they spend. Customer groups come from the supplied customer file.')
    if df.empty:
        st.info('No transactions match the current selection.')
        return
    done = df[df.Status == 'Completed']
    a,b,c = st.columns(3)
    a.metric('Customers with orders', df.customer_id.nunique())
    b.metric('Customers with completed orders', done.customer_id.nunique())
    c.metric('Customers who bought more than once', int((done.groupby('customer_id').size() > 1).sum()))
    dimension = st.radio('Compare customers by', ['Customer type','Region'], horizontal=True, format_func=lambda x: 'Customer group' if x=='Customer type' else x)
    grouped = summarize(df, dimension)
    left,right = st.columns(2)
    with left:
        st.plotly_chart(distribution_donut(df.groupby(dimension).customer_id.nunique(),'Customer distribution','customers'),width='stretch')
    with right:
        st.plotly_chart(ranking_bar_chart(grouped, 'Completed revenue', f'Completed revenue by {dimension.lower()}', 'Amount (₹)'), width='stretch')
    st.dataframe(rupee_table(readable_table(grouped)), width='stretch')
    st.subheader('Customer purchase history')
    profiles = done.groupby('customer_id').agg(**{'Completed orders':('Total','size'), 'Completed revenue':('Total','sum'), 'Last purchase':('Date','max')})
    profiles['Days since last purchase'] = (df.Date.max() - profiles['Last purchase']).dt.days
    profiles = profiles.sort_values('Completed revenue', ascending=False)
    search = st.text_input('Search customer ID')
    if search:
        profiles = profiles[profiles.index.str.contains(search, case=False, regex=False)]
    st.dataframe(rupee_table(profiles), width='stretch')
    st.download_button('Download customer summary', profiles.to_csv(), 'track4_customer_summary.csv', 'text/csv')
    st.caption('“Days since last purchase” counts back from the latest order date in this selection, not today. Purchase counts cover your chosen dates only. Customer groups are supplied in the file; this page does not create new groups.')
    st.subheader('Groups based on buying habits')
    try:
        result,groups=cached_customer_groups(df)
        st.info(f"These {result['selected_k']} groups are calculated from each customer's recent purchases, purchase count, and spending in your current selection. They are separate from the groups supplied in the customer file. A group describes past behavior, not a prediction of future purchases.")
        summary=pd.DataFrame(result['groups']).rename(columns={'customers':'Customers','mean_recency_days':'Average days since purchase','mean_completed_orders':'Average completed orders','mean_spend':'Average order-history spending','revenue':'Revenue (₹)','group':'Group'})
        st.dataframe(summary,hide_index=True,width='stretch')
        st.download_button('Download buying-habit groups',groups.to_csv(index=False),'customer_buying_groups.csv','text/csv')
    except InsufficientData as exc:
        st.info(str(exc))

def campaigns(df, df_all):
    st.header('Marketing')
    st.caption('Spend, clicks, and reported conversions from all selected campaign records.')
    st.info('This page uses date, category, and channel filters. The campaign file has no customer or payment details. It does not show which orders came from each campaign, so we cannot say how much revenue a campaign brought in.')
    state=st.session_state.get(FILTER_STATE_KEY,FilterState())
    raw=filter_support(track4_sources()['campaigns'],state,campaign=True)
    invalid=(raw.clicks>raw.impressions)|(raw.conversions>raw.clicks)
    if invalid.any():
        st.warning(f'{int(invalid.sum())} campaign records in this selection have more clicks than ad views or more conversions than clicks. The totals below retain the original records; compare them cautiously. Model checks exclude impossible counts rather than silently changing them.')
    _, metrics = supporting_data()
    if metrics.empty:
        st.info('No campaign records match the date/category/channel selection.')
        return
    spend = metrics.spend.sum(); conv = metrics.conversions.sum(); clicks = metrics.clicks.sum()
    a,b,c,d = st.columns(4)
    a.metric('Marketing spend', format_currency(spend))
    b.metric('Reported conversions', f'{conv:,}')
    c.metric('Cost per conversion', format_currency(spend/conv) if conv else 'N/A')
    d.metric('Clicks that led to conversions', f'{100*conv/clicks:.1f}%' if clicks else 'N/A')
    left,right = st.columns(2)
    with left:
        st.plotly_chart(distribution_donut(metrics.spend,'Where the budget goes','marketing spend',center_value=compact_currency(spend),money=True),width='stretch')
    with right:
        st.plotly_chart(campaign_funnel(metrics),width='stretch')
    a,b = st.columns(2)
    with a:
        st.plotly_chart(ranking_bar_chart(metrics, 'spend', 'Spend by channel', 'Amount (₹)'), width='stretch')
    with b:
        st.plotly_chart(ranking_bar_chart(metrics.dropna(subset=['Cost per conversion']), 'Cost per conversion', 'Cost per reported conversion', 'Amount (₹)'), width='stretch')
    st.dataframe(rupee_table(readable_table(metrics)), width='stretch')
    st.download_button('Download campaign comparison', readable_table(metrics).to_csv(), 'track4_campaign_comparison.csv', 'text/csv')
    st.caption('A conversion is a result counted by the campaign. The file does not say whether each result is a purchase or another action. Cost per conversion is spend divided by reported results. These counts are not unique customers. A rate is left blank when there are no clicks or ad views to divide by.')

def recommendations(df, df_all):
    st.header('Recommendations')
    st.caption('Use the numbers in this view to decide what to check and what to do next.')
    stock, campaigns = supporting_data()
    st.subheader('Your step-by-step checklist')
    tasks=build_action_plan(df,stock,campaigns)
    if not tasks:
        st.info('No issues to highlight in the selected data.')
    from vaultdata.components.action_checklist import render_action_checklist
    render_action_checklist(tasks)

def source_explorer():
    st.subheader('Official source files')
    sources = track4_sources()
    audit=audit_sources(sources)
    with st.expander('Checks across all five original files'):
        st.dataframe(pd.DataFrame(audit['issues']).rename(columns={'check':'Check','count':'Records','handling':'How handled'}),hide_index=True,width='stretch')
        st.info('Missing-value checks alone do not catch records that disagree. Original files are preserved. These checks describe the full official files, not the sidebar selection.')
    st.caption('Browse the five original files here. Sidebar filters do not change these files. The combined orders table below does use your filters.')
    name = st.selectbox('Inspect source', list(sources))
    raw = sources[name]
    a,b,c = st.columns(3)
    a.metric('Source rows', f'{len(raw):,}')
    b.metric('Missing cells', int(raw.isna().sum().sum()))
    c.metric('Duplicate rows', int(raw.duplicated().sum()))
    search = st.text_input('Search source records', key='source_search')
    if search:
        raw = raw[raw.astype(str).apply(lambda col: col.str.contains(search, case=False, regex=False, na=False)).any(axis=1)]
    st.dataframe(rupee_table(readable_table(raw)), width='stretch', height=250)
    st.download_button('Download source selection', raw.to_csv(index=False), f'track4_{name}.csv', 'text/csv')
    st.divider()

def about(df, df_all):
    st.header('How it works')
    st.markdown('''### Track 4 · The Money Leak
NTR helps you spot business problems, see the numbers behind them, and decide what to check next. It follows the [Track 4 challenge](https://datathon-xi.vercel.app/problem-statements.html#track-4).

### Where the numbers come from
Five files contain 3,000 customers, 250 products, 18,000 orders, 5,000 stock records, and 1,200 campaigns — **27,450 records** in total. Customer and product IDs connect orders to their details. Product IDs connect stock records to categories. Campaigns are checked separately because there is no way to connect them to individual orders.

### Sales, cancellations, and returns
Order value is the number of units multiplied by the selling price after the recorded discount. **Revenue counts completed orders only.** Cancelled, returned, and pending orders are shown separately. Their values do not tell us the actual money lost, refunded, or recoverable. Discounts come from the order record, rather than a comparison with the product's listed price.

### Stock
We use the latest record for each product within your selected dates. **Reported out of stock** means that record marks the product as out of stock or shows no units left. **Running low** means stock is at or below the restock level supplied in the file. **Above restock level** means recorded stock is above that number. These are past records, not live stock. Check the update date and delivery times before ordering more.

### Marketing
A conversion is a result counted by the campaign. The file does not say whether it is a purchase or another action. Cost per conversion is spend divided by reported results. We also show how many ad views led to clicks, and how many clicks led to conversions. A rate is blank when there are no views or clicks to divide by. We cannot tell which orders came from each campaign.

### Customers and sales estimates
Customer IDs let us count purchases by the same person. Customer groups are supplied in the file. Days since last purchase are measured from the last order date in your selection, not today. The sales forecast looks for patterns in past completed sales. We check its estimates against recent days kept out of training. The shaded range shows possible outcomes; it is not a promise of future sales.

### Which filters apply?
Orders use all sidebar filters. Stock uses date and category only. Marketing uses date, category, and channel. The original-file previews on the Data page ignore sidebar filters, so you can inspect each full file.

### What to keep in mind
These are made-up records for learning, not a live business. Money is displayed in Indian rupees (₹) as requested. The source files do not specify a currency, so this is a display choice rather than an exchange-rate conversion. Costs and prices were generated separately, so profit estimates may be unrealistic. The files do not explain cancellations or returns. A highlighted issue is something to check, not proof of its cause.

### LeakLens recommendations
The checklist uses local calculations and clear rules to choose issues worth checking. Locally trained models provide separate estimates and measured results on Model checks. You can assign an owner, mark steps complete, record findings, and download progress. Nothing is sent to a model service.

### Model checks and restock examples
Model checks compares trained methods with simple baselines on later dates kept out of training. The original files contain inconsistent records; the page lists them and explains any modeling exclusions. Some models do not improve on the baseline, so they must not be used to rank individual orders or products. The Sales forecast page can estimate items sold as well as revenue. The Customers page can also build new groups from actual buying habits. The Stock page provides an example restock plan; it cannot account for open purchase orders or unrecorded demand. Recommendations includes a step-by-step checklist that works without an external service.
''')
    done = df[df.Status == 'Completed']
    st.warning(f"In this selection, {int((done['Estimated margin'] < 0).sum()):,} of {len(done):,} completed orders have a selling value below their recorded product cost. Because the sample costs and prices were created separately, these numbers are not reliable business profit figures.")
