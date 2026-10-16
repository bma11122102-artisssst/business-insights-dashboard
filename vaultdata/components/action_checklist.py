"""Session-only action tracking, scoped to the evidence in the current plan."""
import hashlib
import json
import streamlit as st


def render_action_checklist(tasks):
    st.info('Progress is saved for this browser session only. Download your checklist before closing it. Changed supporting numbers start a separate checklist; ticking a step does not change source records or prove a business improvement.')
    tracked = []
    for task in tasks:
        scope = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()[:20]
        with st.container(border=True):
            st.subheader(task['title'])
            st.write(f"Priority: {task['priority']} · Suggested team: {task['owner_role']}")
            st.write(task['supporting_numbers'])
            owner = st.text_input('Assigned to', value=task['owner_role'], key=f'action_owner_{scope}')
            completed = [st.checkbox(step, key=f'action_step_{scope}_{index}') for index, step in enumerate(task['steps'])]
            notes = st.text_area('Findings and next review', key=f'action_notes_{scope}')
            status = 'Done' if all(completed) else 'In progress' if any(completed) else 'Not started'
            st.write(f"Progress: {sum(completed)} of {len(completed)} steps · {status}")
            st.markdown(f"**What to track:** {task['track']}")
            st.write(task['limit'])
            tracked.append({**task, 'assigned_to': owner, 'status': status,
                            'completed_steps': completed, 'review_notes': notes})
    st.download_button('Download step-by-step checklist', json.dumps(tracked, indent=2),
                       'leaklens_checklist.json', 'application/json')
    return tracked
