"""Plotly chart builders with a consistent, restrained VaultData style.

One chart type per business question (per the product spec): line for
trends, bar for rankings, stacked/segmented for composition, scatter for
segmentation, heatmap for time/category patterns, box for distributions.
Donut charts show composition; trends and comparisons use lines and bars.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BRAND_PRIMARY = "#087EED"
BRAND_NAVY = "#071A40"
BRAND_MUTED = "#7E94B2"
CATEGORICAL_PALETTE = ["#087EED", "#24CFC1", "#E6A24A", "#7B7BD2", "#D8756B", "#79AFD6", "#597794"]

_LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    font=dict(family="Inter, -apple-system, sans-serif", size=13, color=BRAND_NAVY),
    margin=dict(l=10, r=10, t=48, b=10),
    colorway=CATEGORICAL_PALETTE,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)


def _style(fig: go.Figure, title: str, y_title: str = "", x_title: str = "") -> go.Figure:
    fig.update_layout(title=dict(text=title, font=dict(size=15)), **_LAYOUT_DEFAULTS)
    if y_title:
        fig.update_yaxes(title=y_title)
    if x_title:
        fig.update_xaxes(title=x_title)
    return fig


def revenue_trend_chart(series: pd.Series, title: str = "Revenue trend") -> go.Figure:
    fig = px.line(series, x=series.index, y=series.values)
    fig.update_traces(line=dict(color=BRAND_PRIMARY, width=2), hovertemplate="%{x|%b %d, %Y}<br>₹%{y:,.2f}<extra></extra>")
    return _style(fig, title, y_title="Revenue (₹)", x_title="Date")


def ranking_bar_chart(df: pd.DataFrame, value_col: str, title: str, x_title: str = "") -> go.Figure:
    ordered = df.sort_values(value_col, ascending=True)
    fig = px.bar(ordered, x=value_col, y=ordered.index, orientation="h")
    monetary = any(term in value_col.lower() for term in ['revenue','value','spend','cost','discount','margin'])
    prefix = '₹' if monetary else ''
    fig.update_traces(marker_color=BRAND_PRIMARY, hovertemplate=f"%{{y}}<br>{prefix}%{{x:,.2f}}<extra></extra>")
    if monetary:
        fig.update_xaxes(tickprefix='₹')
    return _style(fig, title, x_title=x_title or value_col, y_title="")


def composition_bar_chart(df: pd.DataFrame, value_col: str, group_col: str, title: str) -> go.Figure:
    fig = px.bar(df.reset_index(), x=df.index.name or "index", y=value_col, color=group_col, barmode="stack")
    return _style(fig, title, y_title=value_col)


def weekday_hour_heatmap(df: pd.DataFrame, title: str = "Revenue by weekday and hour") -> go.Figure:
    pivot = df.pivot_table(index="Weekday", columns="Hour", values="Total", aggfunc="sum", fill_value=0)
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in weekday_order if d in pivot.index])
    fig = px.imshow(
        pivot,
        color_continuous_scale=["#F1F5F9", BRAND_PRIMARY, BRAND_NAVY],
        aspect="auto",
        labels=dict(color="Revenue (₹)"),
    )
    return _style(fig, title, x_title="Hour of day", y_title="")


def box_distribution_chart(df: pd.DataFrame, value_col: str, group_col: str, title: str) -> go.Figure:
    fig = px.box(df, x=group_col, y=value_col, points=False)
    fig.update_traces(marker_color=BRAND_PRIMARY)
    return _style(fig, title, y_title=value_col, x_title="")


def segmentation_scatter(feature_df: pd.DataFrame, labels, x: str, y: str, title: str = "Transaction segments") -> go.Figure:
    plot_df = feature_df.copy()
    plot_df["Segment"] = [str(l) for l in labels]
    fig = px.scatter(plot_df, x=x, y=y, color="Segment", opacity=0.7)
    return _style(fig, title, x_title=x, y_title=y)


def forecast_chart(
    history: pd.Series,
    forecast: pd.Series,
    lower: pd.Series,
    upper: pd.Series,
    title: str = "Sales forecast",
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=history.index, y=history.values, name="Actual", mode="lines", line=dict(color=BRAND_NAVY, width=2))
    )
    fig.add_trace(
        go.Scatter(
            x=list(upper.index) + list(lower.index[::-1]),
            y=list(upper.values) + list(lower.values[::-1]),
            fill="toself",
            fillcolor="rgba(8,126,237,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Possible range (80%)",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast.index,
            y=forecast.values,
            name="Forecast",
            mode="lines",
            line=dict(color=BRAND_PRIMARY, width=2, dash="dash"),
        )
    )
    fig.update_traces(hovertemplate='%{x|%d %b %Y}<br>₹%{y:,.2f}<extra>%{fullData.name}</extra>',selector=dict(type='scatter'))
    return _style(fig, title, y_title="Revenue (₹)", x_title="Date")


def demand_outlook_chart(rows: list[dict], title: str = "Demand outlook by product line") -> go.Figure:
    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["Product line"], x=df["Observed avg daily demand"], name="Observed", orientation="h", marker_color=BRAND_MUTED))
    fig.add_trace(go.Bar(y=df["Product line"], x=df["Forecast avg daily demand"], name="Forecast", orientation="h", marker_color=BRAND_PRIMARY))
    fig.update_layout(barmode="group")
    return _style(fig, title, x_title="Units / day")


STATUS_COLORS = {'Completed':'#52734E','Cancelled':'#BA6657','Returned':'#D7A15A','Pending':'#9AA5AC','Healthy':'#52734E','Reorder':'#D7A15A','Stockout signal':'#BA6657'}
STATUS_COLORS.update({'Above restock level':'#52734E','Running low':'#D7A15A','Reported out of stock':'#BA6657'})


def distribution_donut(series: pd.Series, title: str, center_label: str, *, center_value: str | None = None, money: bool = False) -> go.Figure:
    """Composition chart; empty/zero-only selections have no invented wedges."""
    values = series[pd.to_numeric(series, errors='coerce').fillna(0) > 0].sort_values(ascending=False)
    fig = go.Figure()
    if len(values):
        colors = [STATUS_COLORS.get(str(name),CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)]) for i,name in enumerate(values.index)]
        prefix='₹' if money else ''
        fig.add_trace(go.Pie(labels=values.index.astype(str), values=values.values, hole=.73, sort=False, marker=dict(colors=colors,line=dict(color='white',width=3)),textinfo='percent',textposition='outside',textfont=dict(size=11),hovertemplate=f'%{{label}}<br>{prefix}%{{value:,.2f}} · %{{percent}}<extra></extra>'))
        total = center_value if center_value is not None else f'{values.sum():,.0f}'
        fig.add_annotation(text=f'<b>{total}</b><br><span style="font-size:11px">{center_label}</span>', x=.5,y=.5,showarrow=False,font=dict(size=25,color=BRAND_NAVY))
    else:
        fig.add_annotation(text='No data in this selection',x=.5,y=.5,showarrow=False,font=dict(color=BRAND_MUTED))
    _style(fig,title)
    fig.update_layout(height=350,margin=dict(l=35,r=35,t=50,b=65),legend=dict(orientation='h',y=-.12,x=.5,xanchor='center',yanchor='top',font=dict(size=10)))
    return fig


def outcome_trend_chart(df: pd.DataFrame) -> go.Figure:
    weekly = df.groupby([pd.Grouper(key='Date',freq='W'),'Status']).size().rename('Orders').reset_index()
    fig = px.bar(weekly,x='Date',y='Orders',color='Status',color_discrete_map=STATUS_COLORS, barmode='stack')
    return _style(fig,'Weekly order outcomes',y_title='Orders',x_title='Week ending')


def campaign_funnel(metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Funnel(y=['Ad views','Clicks','Reported conversions'],x=[metrics.impressions.sum(),metrics.clicks.sum(),metrics.conversions.sum()],textinfo='value+percent initial',marker=dict(color=['#C4D2B7','#8EA67B',BRAND_PRIMARY]),connector=dict(line=dict(color='#DDE5D5'))))
    _style(fig,'From ad views to reported results')
    fig.update_layout(height=350,showlegend=False)
    return fig
