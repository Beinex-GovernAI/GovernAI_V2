import streamlit as st
import pandas as pd
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.monitoring_svc import DEFAULT_THRESHOLDS, ingest_metrics_from_csv, get_metrics
from services.audit_svc import get_audit_logs

st.set_page_config(page_title="Monitoring", page_icon="📈", layout="wide")

st.title("📈 System Monitoring & Alerts")

db = SessionLocal()
current_user = st.session_state.get("current_user", "Admin")

systems = get_systems(db)

if not systems:
    st.warning("No systems found.")
else:
    system_names = {sys.id: sys.name for sys in systems}
    selected_sys_id = st.selectbox("Select AI System", options=list(system_names.keys()), format_func=lambda x: system_names[x])
    
    selected_sys = next(s for s in systems if s.id == selected_sys_id)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Metric Data (CSV)")
        st.info(
            "Upload a CSV with columns **metric_name** and **metric_value** to ingest real "
            "monitoring data. Threshold breaches will automatically trigger status updates "
            "and audit logging (the Golden Thread)."
        )
        st.write(f"**Supported metrics & thresholds:** {DEFAULT_THRESHOLDS}")

        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file is not None:
            if st.button("Ingest CSV"):
                try:
                    result = ingest_metrics_from_csv(db, selected_sys_id, uploaded_file, current_user)
                    
                    st.success(
                        f"Ingested {len(result['ingested'])} of {result['total_rows']} rows successfully."
                    )
                    
                    if result["errors"]:
                        st.warning("Some rows had issues:")
                        for err in result["errors"]:
                            st.write(f"- {err}")
                    
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Failed to process CSV: {e}")

        st.subheader("Metric History")
        metrics = get_metrics(db, selected_sys_id)
        if metrics:
            metric_data = []
            for m in metrics:
                metric_data.append({
                    "Timestamp": m.timestamp,
                    "Metric": m.metric_name,
                    "Value": m.metric_value,
                    "Threshold": m.threshold_value,
                    "Breached": "Yes" if m.is_breached else "No"
                })
            df = pd.DataFrame(metric_data)
            st.dataframe(df, width='stretch')
        else:
            st.write("No metrics recorded yet.")

    with col2:
        st.subheader("Live Status")
        if selected_sys.compliance_status == "Compliant":
            st.success("Status: Compliant")
        elif selected_sys.compliance_status == "Non-Compliant":
            st.error("Status: Non-Compliant")
        elif selected_sys.compliance_status == "At Risk":
            st.warning("Status: At Risk")
        else:
            st.info("Status: Pending")

        st.subheader("Audit Trail")
        logs = get_audit_logs(db, selected_sys_id)
        if logs:
            for log in logs[:10]:
                with st.expander(f"**{log.action}** - {log.timestamp.split('T')[0]}"):
                    st.write(f"**User:** {log.user}")
                    st.json(log.details)
        else:
            st.write("No audit logs.")

db.close()