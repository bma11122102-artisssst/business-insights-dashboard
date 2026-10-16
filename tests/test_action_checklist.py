from streamlit.testing.v1 import AppTest

SCRIPT = '''
import streamlit as st
from vaultdata.components.action_checklist import render_action_checklist
value=st.number_input('Evidence count', value=3)
task={'id':'check','title':'Check records','priority':'High','owner_role':'Stock team','supporting_numbers':str(value)+' records','steps':['Count stock','Review source'],'track':'Unresolved records','limit':'Check before ordering.'}
st.session_state['exported']=render_action_checklist([task])
'''


def test_action_progress_export_and_changed_evidence():
    app=AppTest.from_string(SCRIPT).run()
    assert not app.exception
    app.checkbox[0].check().run()
    app.text_input[0].set_value('Purchasing lead').run()
    app.text_area[0].set_value('Count scheduled tomorrow').run()
    task=app.session_state['exported'][0]
    assert task['status']=='In progress'
    assert task['completed_steps']==[True,False]
    assert task['assigned_to']=='Purchasing lead'
    assert task['review_notes']=='Count scheduled tomorrow'
    app.checkbox[1].check().run()
    assert app.session_state['exported'][0]['status']=='Done'
    app.number_input[0].set_value(4).run()
    assert not app.exception
    assert app.session_state['exported'][0]['status']=='Not started'
    assert app.session_state['exported'][0]['assigned_to']=='Stock team'
