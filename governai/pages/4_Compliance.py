import streamlit as st
import os
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.compliance_svc import generate_checklists, get_compliance_score, update_compliance_record

st.set_page_config(page_title="Compliance", page_icon="📋", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title(" Compliance Checklists")

db = SessionLocal()
systems = get_systems(db)

# Matches the same tier values used on the Dashboard
TIER_CLASS = {
    "High": "tier-high",
    "Limited": "tier-limited",
    "Minimal": "tier-minimal",
    "Pending": "tier-pending",
    "Prohibited": "tier-high",
}

if not systems:
    st.warning("No systems found.")
else:
    system_names = {sys.id: sys.name for sys in systems}
    selected_sys_id = st.selectbox(
        "Select AI System",
        options=list(system_names.keys()),
        format_func=lambda x: system_names[x],
    )

    selected_sys = next(s for s in systems if s.id == selected_sys_id)
    tier = selected_sys.risk_tier or "Pending"
    tier_class = TIER_CLASS.get(tier, "tier-pending")

    # ── System overview card ──
    st.markdown(
        f"""
        <div class="gov-card">
            <div class="gov-card-title">{selected_sys.name}</div>
            <div class="gov-card-sub">{selected_sys.owner or ""}</div>
            <div style="margin-top: 0.75rem;">
                <span class="{tier_class}">{tier}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if tier == "Pending":
        st.info("Please complete the Risk Assessment first to generate the compliance checklist.")
    elif tier == "Prohibited":
        st.error("Prohibited systems cannot be made compliant under the EU AI Act.")
    else:
        records = generate_checklists(db, selected_sys_id)
        score = get_compliance_score(db, selected_sys_id)

        st.markdown('<p class="section-label">Overall Completeness</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="pct-badge">{score}%</span>', unsafe_allow_html=True)
        st.progress(score / 100.0)

        frameworks = sorted(set(r.framework for r in records))

        for framework_name in frameworks:
            framework_records = [r for r in records if r.framework == framework_name]
            framework_score = get_compliance_score(db, selected_sys_id, framework=framework_name)

            st.markdown(f'<p class="section-label">{framework_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<span class="pct-badge">{framework_score}% complete</span>', unsafe_allow_html=True)
            st.progress(framework_score / 100.0)

            for record in framework_records:
                status_class = "status-compliant" if record.is_met else "status-pending"
                status_label = "Yes" if record.is_met else "No"

                st.markdown(
                    f"""
                    <div class="gov-card">
                        <div class="gov-card-title">{record.control_id}</div>
                        <div class="gov-card-sub">{record.control_description}</div>
                        <div style="margin-top: 0.5rem;">
                            <span class="{status_class}">{status_label}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.expander(record.control_id):
                    with st.form(f"form_{record.id}"):
                        is_met = st.checkbox("Control Met?", value=bool(record.is_met))
                        evidence = st.text_input(
                            "Evidence Link (URL or doc ref)",
                            value=record.evidence_link or "",
                            placeholder="URL or document reference...",
                        )

                        if st.form_submit_button("Save Control"):
                            current_user = st.session_state.get("current_user", "System")
                            update_compliance_record(
                                db, record.id, 1 if is_met else 0, evidence, current_user
                            )
                            st.success("Saved!")
                            st.rerun()
db.close()