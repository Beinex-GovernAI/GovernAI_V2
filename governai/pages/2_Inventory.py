import streamlit as st
import os
from database.db import SessionLocal
from services.ai_system_svc import get_systems, create_system
from reports.report_gen import generate_pdf_report

st.set_page_config(page_title="Inventory", page_icon="📝", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title("📝 AI System Inventory")

db = SessionLocal()
current_user = st.session_state.get("current_user", "Admin")

TIER_CLASS = {
    "High": "tier-high",
    "Limited": "tier-limited",
    "Minimal": "tier-minimal",
    "Pending": "tier-pending",
    "Prohibited": "tier-high",
}

STATUS_CLASS = {
    "Compliant": "status-compliant",
    "Non-Compliant": "status-noncompliant",
    "At Risk": "status-atrisk",
    "Pending": "status-pending",
}

tab1, tab2 = st.tabs(["View Systems", "Add New System"])

with tab1:
    st.markdown('<p class="section-label">Registered AI Systems</p>', unsafe_allow_html=True)
    systems = get_systems(db)

    if systems:
        for sys in systems:
            tier = sys.risk_tier or "Pending"
            status = sys.compliance_status or "Pending"
            tier_class = TIER_CLASS.get(tier, "tier-pending")
            status_class = STATUS_CLASS.get(status, "status-pending")

            # ── System summary card ──
            st.markdown(
                f"""
                <div class="gov-card">
                    <div class="gov-card-title">{sys.name}</div>
                    <div class="gov-card-sub">Owner: {sys.owner}</div>
                    <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem;">
                        <span class="{tier_class}">{tier}</span>
                        <span class="{status_class}">{status}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(sys.name):
                st.markdown(f"""
                <div style="line-height: 2;">
                    <span style="color:#7D9A7D;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Business Purpose</span><br>
                    <span style="color:#E6EDF3;">{sys.business_purpose or 'N/A'}</span>
                </div>
                <div style="margin-top: 0.75rem; line-height: 2;">
                    <span style="color:#7D9A7D;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Model Vendor</span><br>
                    <span style="color:#E6EDF3;">{sys.model_vendor or 'N/A'}</span>
                </div>
                <div style="margin-top: 0.75rem; line-height: 2;">
                    <span style="color:#7D9A7D;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Model Type</span><br>
                    <span style="color:#E6EDF3;">{sys.model_type or 'N/A'}</span>
                </div>
                <div style="margin-top: 0.75rem; line-height: 2;">
                    <span style="color:#7D9A7D;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Model Source</span><br>
                    <span style="color:#E6EDF3;">{sys.model_source or 'N/A'}</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                if st.button("Export Audit Report (PDF)", key=f"export_{sys.id}"):
                    try:
                        report_path = f"report_{sys.id}.pdf"
                        generate_pdf_report(sys.id, report_path)

                        with open(report_path, "rb") as f:
                            pdf_bytes = f.read()

                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name=f"GovernAI_Audit_{sys.name}.pdf",
                            mime="application/pdf",
                            key=f"download_{sys.id}",
                        )
                        os.remove(report_path)
                    except Exception as e:
                        st.error(f"Failed to generate report: {e}")
    else:
        st.info("No AI systems registered yet.")

with tab2:
    st.markdown('<p class="section-label">Register New AI System</p>', unsafe_allow_html=True)
    with st.form("new_system_form"):
        name = st.text_input("System Name")
        owner = st.text_input("Owner (Department/Person)")
        business_purpose = st.text_area("Business Purpose")
        model_vendor = st.text_input("Model Vendor (e.g., OpenAI, Anthropic, In-house)")

        col1, col2 = st.columns(2)
        with col1:
            model_type = st.selectbox("Model Type", ["LLM", "Classical ML", "Computer Vision", "Agentic AI"])
        with col2:
            model_source = st.selectbox("Model Source", ["Proprietary", "Open Source"])

        agentic_trace_required = st.radio("Is Agentic Trace Required?", ["Yes", "No"], index=1)

        submit_button = st.form_submit_button("Register System")

        if submit_button:
            if name and owner:
                system_data = {
                    "name": name,
                    "owner": owner,
                    "business_purpose": business_purpose,
                    "model_vendor": model_vendor,
                    "model_type": model_type,
                    "model_source": model_source,
                    "agentic_trace_required": agentic_trace_required,
                }
                create_system(db, system_data, current_user)
                st.success(f"System '{name}' registered successfully!")
                st.rerun()
            else:
                st.error("Name and Owner are required fields.")

db.close()