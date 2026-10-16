"""Deterministic step-by-step recommendations, fully usable without a cloud key."""
from vaultdata.analytics.leakage import summarize
from vaultdata.viz.formatting import format_currency

def build_action_plan(transactions,stock,campaigns):
    tasks=[]
    conflicts=stock[(stock.stockout_flag==1)&(stock.stock_on_hand>0)]
    if len(conflicts):
        tasks.append({'id':'stock-record-check','priority':'High','title':'Check stock records that disagree','owner_role':'Stock team',
            'supporting_numbers':f'{len(conflicts)} latest selected records say out of stock while listing units left.',
            'steps':['Find these products in the Stock page.','Count the actual units and check the record date.','Correct the flag or quantity in the source system before deciding what to order.'],
            'track':'Number of conflicting stock records still unresolved.','limit':'A flag is not proof of a physical stockout. Stock uses date/category filters only.'})
    if len(transactions):
        ranking=summarize(transactions,'Product line')
        if len(ranking) and ranking.iloc[0]['Affected value']>0:
            category=ranking.index[0];row=ranking.iloc[0]
            tasks.append({'id':'order-fallout-check','priority':'High' if row.Orders>=100 else 'Medium','title':f'Find out why {category} orders were cancelled or returned','owner_role':'Sales and returns team',
                'supporting_numbers':f"{format_currency(row['Affected value'])} across a category with {int(row.Orders):,} orders; {row['Fallout rate %']:.1f}% cancelled or returned.",
                'steps':['Open Sales and compare this category by region and shopping channel.','Read cancellation and return reasons in the order system; these reasons are not supplied here.','Separate delivery, product-quality, and customer-request issues before choosing an intervention.','Track the cancellation and return rates over the next comparable period.'],
                'track':'Cancelled and returned orders as a share of all category orders; include order counts.','limit':'Affected order value is not promised recovery. These records cannot establish the cause.'})
    low=stock[(stock.stock_on_hand<=stock.reorder_threshold)&(stock.stockout_flag!=1)]
    if len(low):
        tasks.append({'id':'restock-review','priority':'Medium','title':'Review products that are running low','owner_role':'Stock and purchasing team',
            'supporting_numbers':f'{len(low)} latest selected product records are at or below the supplied restock level.',
            'steps':['Confirm current stock and expected supplier delivery dates.','Open the restock planner and review recent sales, record age, and its assumptions.','Check budget and outstanding purchase orders before approving quantities.'],
            'track':'Products below their restock level, stock record age, and actual availability.','limit':'The planner is a scenario. Outstanding orders, holding costs, and lost demand are missing.'})
    valid=campaigns.dropna(subset=['Cost per conversion'])
    if len(valid)>=2:
        expensive=valid['Cost per conversion'].idxmax();cheap=valid['Cost per conversion'].idxmin()
        if valid.loc[expensive,'Cost per conversion']>valid.loc[cheap,'Cost per conversion']:
            tasks.append({'id':'campaign-results-check','priority':'Medium','title':f'Check the cost of {expensive} campaign results','owner_role':'Marketing team',
                'supporting_numbers':f"{format_currency(valid.loc[expensive,'Cost per conversion'])} per reported conversion versus {format_currency(valid.loc[cheap,'Cost per conversion'])} on {cheap}.",
                'steps':['Check the data-quality warnings for impossible click or conversion counts.','Confirm that the channels count the same type of conversion.','Check result quality, then run a small controlled budget test if the comparison is still meaningful.'],
                'track':'Cost per valid reported conversion and the number and quality of those results.','limit':'Campaigns cannot be connected to individual orders, so no revenue attribution or ROAS is calculated.'})
    return tasks
