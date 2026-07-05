import streamlit as st
import os

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
    ("pages/1_Dashboard.py", "Dashboard", "High-level portfolio view.", "📊"),
    ("pages/2_Inventory.py", "Inventory", "Central registry of all AI systems.", "📂"),
    ("pages/3_Risk_Setup.py", "Risk Setup", "Questionnaire for EU AI Act risk.", "⚖️"),
    ("pages/4_Compliance.py", "Compliance", "Checklists and framework mappings.", "✅"),
    ("pages/5_Monitoring.py", "Monitoring", "Real-time metrics and alerts.", "📈"),
]

# Create a clean grid layout (3 columns on the first row, 2 on the second)
cols1 = st.columns(3)
cols2 = st.columns(3)

for i, (page_path, name, desc, icon) in enumerate(nav_items):
    # Place first 3 items in the first row, next 2 in the second row
    col = cols1[i] if i < 3 else cols2[i - 3]
    with col:
        st.page_link(page_path, label=f"**{name}**\n\n{desc}", icon=icon, use_container_width=True)

# Sidebar Role Selector
st.sidebar.markdown('<p class="section-label" style="margin-top:0;">Simulation Identity</p>', unsafe_allow_html=True)
role = st.sidebar.selectbox(
    "Current User:",
    ["Admin", "Compliance Officer", "Engineer"]
)

st.session_state["current_user"] = role

st.sidebar.markdown(f"""
<div class="gov-card" style="margin-top:0.75rem;">
    <div class="gov-card-sub">Logged in as</div>
    <div class="gov-card-title" style="margin-top:0.2rem;">{role}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.info("This lightweight role selector drives the audit log trail to demonstrate realistic governance workflows.")