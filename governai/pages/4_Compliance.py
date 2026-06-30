import streamlit as st
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.compliance_svc import generate_checklists, get_compliance_score, update_compliance_record

st.set_page_config(page_title="Compliance", page_icon="📋", layout="wide")

st.title("📋 Compliance Checklists")

db = SessionLocal()
systems = get_systems(db)

if not systems:
    st.warning("No systems found.")
else:
    system_names = {sys.id: sys.name for sys in systems}
    selected_sys_id = st.selectbox("Select AI System", options=list(system_names.keys()), format_func=lambda x: system_names[x])
    
    selected_sys = next(s for s in systems if s.id == selected_sys_id)
    
    st.subheader(f"Compliance Mapping for: {selected_sys.name}")
    st.write(f"**Risk Tier:** {selected_sys.risk_tier}")
    
    if selected_sys.risk_tier == "Pending":
        st.info("Please complete the Risk Assessment first to generate the compliance checklist.")
    elif selected_sys.risk_tier == "Prohibited":
        st.error("Prohibited systems cannot be made compliant under the EU AI Act.")
    else:
        # Auto-generate records for ALL supported frameworks if they don't exist
        records = generate_checklists(db, selected_sys_id)
        
        score = get_compliance_score(db, selected_sys_id)
        st.progress(score / 100.0, text=f"Overall Completeness Score: {score}%")

        # Group records by their actual framework instead of assuming EU AI Act
        frameworks = sorted(set(r.framework for r in records))

        for framework_name in frameworks:
            framework_records = [r for r in records if r.framework == framework_name]
            framework_score = get_compliance_score(db, selected_sys_id, framework=framework_name)

            st.markdown(f"### Framework: {framework_name}")
            st.progress(framework_score / 100.0, text=f"{framework_name} Completeness: {framework_score}%")

            for record in framework_records:
                with st.expander(f"{record.control_id}: {record.control_description}"):
                    with st.form(f"form_{record.id}"):
                        is_met = st.checkbox("Control Met?", value=bool(record.is_met))
                        evidence = st.text_input("Evidence Link (URL or doc ref)", value=record.evidence_link or "")
                        
                        if st.form_submit_button("Save"):
                            update_compliance_record(db, record.id, 1 if is_met else 0, evidence)
                            st.success("Saved!")
                            st.rerun()

db.close()