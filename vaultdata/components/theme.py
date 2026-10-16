"""Presentation enhancements on the original Streamlit app."""
import streamlit as st

def apply_theme():
    st.markdown('''<style>
    .stApp {background:#f5f8fc;color:#071a40}
    [data-testid="stSidebar"] {background:#eaf3fe;border-right:1px solid #dce7f5}
    .block-container {padding-top:2rem;max-width:1450px}
    h1,h2,h3 {letter-spacing:-.035em;color:#071a40}
    [data-testid="stMetric"] {background:white;border:1px solid #dce7f5;border-radius:12px;padding:18px 20px}
    [data-testid="stMetricLabel"] {color:#526a87;font-size:.82rem}
    [data-testid="stMetricValue"] {font-size:1.65rem}
    [data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:12px}
    .stButton>button,.stDownloadButton>button {border-radius:7px;border-color:#d4e2f3}
    [data-testid="stPlotlyChart"] {border-radius:12px;overflow:hidden}
    [data-testid="stProgress"] {margin:4px 0 12px}
    [data-testid="stCaptionContainer"] {display:none !important}
    [data-testid="stDataFrame"] {border-radius:10px}
    [data-testid="stVerticalBlockBorderWrapper"] {background:rgba(255,255,255,.68)}
    .stButton>button[kind="primary"] {background:#087eed;color:white;border-color:#087eed}
    </style>''', unsafe_allow_html=True)
