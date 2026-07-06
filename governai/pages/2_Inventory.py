import streamlit as st
import os
from database.db import SessionLocal
from services.ai_system_svc import get_systems, create_system, update_system, delete_system
from reports.report_gen import generate_pdf_report

st.set_page_config(page_title="Inventory", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title(" AI System Inventory")

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

            # ── System summary card with top-right delete icon ──
            delete_pending = st.session_state.get(f'delete_confirm_{sys.id}', False)

            # Give the icon column a bit more room when showing confirm/cancel
            card_col, icon_col = st.columns([9, 3]) if delete_pending else st.columns([12, 1])

            with card_col:
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
            with icon_col:
                st.markdown('<div class="icon-btn-spacer"></div>', unsafe_allow_html=True)
                if delete_pending:
                    # Inline confirm/cancel, right where the trash icon was — no scrolling, no boxed warning
                    confirm_col, cancel_col = st.columns(2)
                    with confirm_col:
                        if st.button("✅", key=f"confirm_top_{sys.id}", help=f"Confirm delete of '{sys.name}'"):
                            try:
                                delete_system(db, sys.id, current_user)
                                st.session_state.pop(f'delete_confirm_{sys.id}', None)
                                st.toast(f"'{sys.name}' deleted.", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.session_state.pop(f'delete_confirm_{sys.id}', None)
                                st.toast(f"Failed to delete '{sys.name}': {e}", icon="⚠️")
                    with cancel_col:
                        if st.button("✖️", key=f"cancel_top_{sys.id}", help="Cancel"):
                            st.session_state.pop(f'delete_confirm_{sys.id}', None)
                            st.rerun()
                else:
                    if st.button("🗑️", key=f"top_delete_{sys.id}", help="Delete this system"):
                        st.session_state[f'delete_confirm_{sys.id}'] = True
                        st.rerun()

            # Auto-expand the card only while editing (delete is handled inline above, no expansion needed)
            expanded = st.session_state.get(f'editing_{sys.id}', False)

            with st.expander(sys.name, expanded=expanded):
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

                # Edit control (delete is triggered via the 🗑️ icon at the top of the card)
                if st.button("Edit System", key=f"edit_btn_{sys.id}"):
                    st.session_state[f'editing_{sys.id}'] = True

                # If user chose to edit, show a pre-filled form
                if st.session_state.get(f'editing_{sys.id}'):
                    with st.form(f"edit_form_{sys.id}"):
                        name_e = st.text_input("System Name", value=sys.name)
                        owner_e = st.text_input("Owner (Department/Person)", value=sys.owner)
                        business_purpose_e = st.text_area("Business Purpose", value=sys.business_purpose or '')
                        model_vendor_e = st.text_input("Model Vendor (e.g., OpenAI, Anthropic, In-house)", value=sys.model_vendor or '')

                        col1e, col2e = st.columns(2)
                        with col1e:
                            TYPES = ["LLM", "Classical ML", "Computer Vision", "Agentic AI"]
                            try:
                                type_index = TYPES.index(sys.model_type) if sys.model_type in TYPES else 0
                            except Exception:
                                type_index = 0
                            model_type_e = st.selectbox("Model Type", TYPES, index=type_index)
                        with col2e:
                            SOURCES = ["Proprietary", "Open Source"]
                            try:
                                src_index = SOURCES.index(sys.model_source) if sys.model_source in SOURCES else 0
                            except Exception:
                                src_index = 0
                            model_source_e = st.selectbox("Model Source", SOURCES, index=src_index)

                        agentic_trace_required_e = st.radio("Is Agentic Trace Required?", ["Yes", "No"], index=0 if (sys.agentic_trace_required == "Yes") else 1)

                        submit_edit = st.form_submit_button("Update System", key=f"submit_edit_{sys.id}")

                        if submit_edit:
                            updated_data = {
                                "name": name_e,
                                "owner": owner_e,
                                "business_purpose": business_purpose_e,
                                "model_vendor": model_vendor_e,
                                "model_type": model_type_e,
                                "model_source": model_source_e,
                                "agentic_trace_required": agentic_trace_required_e,
                            }
                            try:
                                update_system(db, sys.id, updated_data, current_user)
                                st.success(f"System '{name_e}' updated successfully!")
                                st.session_state.pop(f'editing_{sys.id}', None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update system: {e}")

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