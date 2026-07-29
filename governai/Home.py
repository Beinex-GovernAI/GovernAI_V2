import streamlit as st
import os
from services.permissions_svc import PERMISSIONS

st.set_page_config(
    page_title="GovernAI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title("GovernAI: AI Governance Platform")

st.markdown("""
<p style="color:#E6EDF3;font-size:0.95rem;line-height:1.6;max-width:720px;">
Welcome to <strong style="color:#FFFFFF;">GovernAI</strong>. This is your centralized portal for
managing AI systems, assessing risk against the EU AI Act and NIST AI Risk Management Framework, mapping compliance controls, and
monitoring operational safety in real-time.
</p>
""", unsafe_allow_html=True)

st.markdown('<p class="section-label">Navigate the Platform</p>', unsafe_allow_html=True)

nav_items = [
    ("pages/1_Dashboard.py", "Dashboard", "High-level portfolio view.", ":material/dashboard:"),
    ("pages/2_Inventory.py", "Inventory", "Central registry of all AI systems.", ":material/inventory_2:"),
    ("pages/3_Risk_Setup.py", "Risk Setup", "Questionnaire for EU AI Act risk.", ":material/balance:"),
    ("pages/4_Compliance.py", "Compliance", "Checklists and framework mappings.", ":material/verified:"),
    ("pages/5_Monitoring.py", "Monitoring", "Real-time metrics and alerts.", ":material/monitoring:"),
]

cols1 = st.columns(3)
cols2 = st.columns(3)

for i, (page_path, name, desc, icon) in enumerate(nav_items):
    col = cols1[i] if i < 3 else cols2[i - 3]
    with col:
        st.page_link(page_path, label=f"**{name}**\n\n{desc}", icon=icon, use_container_width=True)

# Sidebar Role Selector
st.sidebar.markdown('<p class="section-label" style="margin-top:0;">Simulation Identity</p>', unsafe_allow_html=True)

role_options = list(PERMISSIONS.keys())
current_role_value = st.session_state.get("current_user", "Admin")
default_index = role_options.index(current_role_value) if current_role_value in role_options else 0

role = st.sidebar.selectbox(
    "Current User:",
    role_options,
    index=default_index,
    key="role_selector"
)

st.session_state["current_user"] = role

st.sidebar.markdown(f"""
<div class="gov-card" style="margin-top:0.75rem;">
    <div class="gov-card-sub">Logged in as</div>
    <div class="gov-card-title" style="margin-top:0.2rem;">{role}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.info("This role selector now drives real permissions across the app, not just the audit log trail.")