import streamlit as st
from vaultdata.data.track4 import is_track4
from views.track4 import campaigns

def render(df_filtered, df_all):
    if is_track4(df_all):
        campaigns(df_filtered, df_all)
    else:
        st.header('Marketing')
        st.info('Select Track 4 · The Money Leak in the sidebar to analyze the official campaigns.csv. The original demo and uploaded transaction CSV do not contain campaign records.')
