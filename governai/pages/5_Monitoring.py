import streamlit as st
import os
import pandas as pd
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.monitoring_svc import DEFAULT_THRESHOLDS, ingest_metrics_from_csv, get_metrics
from services.audit_svc import get_audit_logs

st.set_page_config(page_title="Monitoring", page_icon="📈", layout="wide")

import streamlit as st
import os
import pandas as pd
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.monitoring_svc import DEFAULT_THRESHOLDS, ingest_metrics_from_csv, get_metrics
from services.audit_svc import get_audit_logs

st.set_page_config(page_title="Monitoring", page_icon="📈", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def render_metric_table(metric_data):
    rows_html = ""
    for row in metric_data:
        breached_class = "status-noncompliant" if row["Breached"] == "Yes" else "status-compliant"
        rows_html += (
            "<tr>"
            f"<td>{row['Timestamp']}</td>"
            f"<td>{row['Metric']}</td>"
            f"<td>{row['Value']}</td>"
            f"<td>{row['Threshold']}</td>"
            f"<td><span class='{breached_class}'>{row['Breached']}</span></td>"
            "</tr>"
        )

    table_html = (
        "<table class='gov-table'>"
        "<thead><tr>"
        "<th>Timestamp</th><th>Metric</th><th>Value</th><th>Threshold</th><th>Breached</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
 

load_css()

st.title("System Monitoring & Alerts")

db = SessionLocal()
current_user = st.session_state.get("current_user", "Admin")

systems = get_systems(db)

if not systems:
    st.warning("No systems found.")
else:
    st.markdown('<p class="section-label">Select System</p>', unsafe_allow_html=True)
    system_names = {sys.id: sys.name for sys in systems}
    selected_sys_id = st.selectbox(
        "Select AI System",
        options=list(system_names.keys()),
        format_func=lambda x: system_names[x],
        label_visibility="collapsed",
    )

    selected_sys = next(s for s in systems if s.id == selected_sys_id)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<p class="section-label">Upload Metric Data (CSV)</p>', unsafe_allow_html=True)
        st.info(
            "Upload a CSV with columns **metric_name** and **metric_value** to ingest real "
            "monitoring data. Threshold breaches will automatically trigger status updates "
            "and audit logging (the Golden Thread)."
        )

        st.markdown(f"""
        <div class="gov-card">
            <div class="gov-card-title" style="font-size:0.82rem;">Supported Metrics & Thresholds</div>
            <div class="gov-card-sub" style="margin-top:0.4rem;">{DEFAULT_THRESHOLDS}</div>
        </div>
        """, unsafe_allow_html=True)

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

        st.markdown('<p class="section-label">Metric History</p>', unsafe_allow_html=True)
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
            render_metric_table(metric_data)
        else:
            st.markdown('<p style="color:#7D9A7D;font-size:0.85rem;">No metrics recorded yet.</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<p class="section-label">Live Status</p>', unsafe_allow_html=True)

        status = selected_sys.compliance_status or "Pending"
        status_class = {
            "Compliant": "status-compliant",
            "Non-Compliant": "status-noncompliant",
            "At Risk": "status-atrisk",
            "Pending": "status-pending"
        }.get(status, "status-pending")

        st.markdown(f"""
        <div class="gov-card">
            <span class="{status_class}">{status}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="section-label">Audit Trail</p>', unsafe_allow_html=True)
        logs = get_audit_logs(db, selected_sys_id)
        if logs:
            for log in logs[:10]:
                with st.expander(f"{log.action} — {log.timestamp.split('T')[0]}"):
                    st.markdown(f"<p style='color:#E6EDF3;font-size:0.85rem;'><strong>User:</strong> {log.user}</p>", unsafe_allow_html=True)
                    st.json(log.details)
        else:
            st.markdown('<p style="color:#7D9A7D;font-size:0.85rem;">No audit logs.</p>', unsafe_allow_html=True)

db.close()