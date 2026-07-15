import streamlit as st
import os
from database.db import SessionLocal
from services.ai_system_svc import get_systems

st.set_page_config(page_title="Dashboard", page_icon="", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title("Dashboard")

db = SessionLocal()
systems = get_systems(db)

total_systems = len(systems)
compliant = sum(1 for s in systems if s.compliance_status == "Compliant")
non_compliant = sum(1 for s in systems if s.compliance_status == "Non-Compliant")
at_risk = sum(1 for s in systems if s.compliance_status == "At Risk")
pending = sum(1 for s in systems if s.compliance_status == "Pending")

# Top metrics row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Systems", total_systems)
col2.metric("Compliant", compliant)
col3.metric("At Risk", at_risk)
col4.metric("Non-Compliant", non_compliant)
col5.metric("Pending", pending)

st.markdown("---")

# System overview table
st.markdown('<p class="section-label">Registered AI Systems</p>', unsafe_allow_html=True)

if systems:
    for sys in systems:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

            with col1:
                st.markdown(f"**{sys.name}**")
                st.markdown(f"<span style='color:#7D8590;font-size:0.82rem'>{sys.owner}</span>", unsafe_allow_html=True)

            with col2:
                st.markdown('<span style="color:#7D8590;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px">Model</span>', unsafe_allow_html=True)
                st.markdown(f"<span style='color:#E6EDF3;font-size:0.88rem'>{sys.model_type or 'N/A'}</span>", unsafe_allow_html=True)

            with col3:
                st.markdown('<span style="color:#7D8590;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px">Risk Tier</span>', unsafe_allow_html=True)
                tier = sys.risk_tier or "Pending"
                tier_class = {
                    "High": "tier-high",
                    "Limited": "tier-limited",
                    "Minimal": "tier-minimal",
                    "Pending": "tier-pending",
                    "Prohibited": "tier-high"
                }.get(tier, "tier-pending")
                st.markdown(f'<span class="{tier_class}">{tier}</span>', unsafe_allow_html=True)

            with col4:
                st.markdown('<span style="color:#7D8590;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px">Status</span>', unsafe_allow_html=True)
                status = sys.compliance_status or "Pending"
                status_class = {
                    "Compliant": "status-compliant",
                    "Non-Compliant": "status-noncompliant",
                    "At Risk": "status-atrisk",
                    "Pending": "status-pending"
                }.get(status, "status-pending")
                st.markdown(f'<span class="{status_class}">{status}</span>', unsafe_allow_html=True)

            st.markdown("<hr style='border:none;border-top:1px solid #21262D;margin:0.5rem 0'>", unsafe_allow_html=True)
else:
    st.info("No AI systems registered yet. Add a system in the Inventory.")

# Summary section
st.markdown('<p class="section-label">Compliance Overview</p>', unsafe_allow_html=True)

if total_systems > 0:
    compliance_rate = int((compliant / total_systems) * 100)
    st.progress(compliance_rate / 100, text=f"Overall Compliance Rate: {compliance_rate}%")

    col1, col2 = st.columns(2)
    with col1:
        high_risk_count = sum(1 for s in systems if s.risk_tier == "High")
        st.markdown(f"""
        <div style='background:#161B22;border:1px solid #21262D;border-left:3px solid #E05252;border-radius:6px;padding:1rem;'>
            <p style='color:#7D8590;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;margin:0'>High Risk Systems</p>
            <p style='color:#E05252;font-size:1.8rem;font-weight:700;margin:0.25rem 0 0 0'>{high_risk_count}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        breached_count = sum(1 for s in systems if s.compliance_status == "Non-Compliant")
        st.markdown(f"""
        <div style='background:#161B22;border:1px solid #21262D;border-left:3px solid #F0A500;border-radius:6px;padding:1rem;'>
            <p style='color:#7D8590;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;margin:0'>Breached Systems</p>
            <p style='color:#F0A500;font-size:1.8rem;font-weight:700;margin:0.25rem 0 0 0'>{breached_count}</p>
        </div>
        """, unsafe_allow_html=True)

db.close()

