import streamlit as st
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.monitoring_svc import DEFAULT_THRESHOLDS, ingest_metrics_from_csv, get_metrics
from services.audit_svc import get_audit_logs

st.set_page_config(page_title="Monitoring", layout="wide")


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


def build_metric_data(metric_list):
    return [{
        "Timestamp": m.timestamp,
        "Metric": m.metric_name,
        "Value": m.metric_value,
        "Threshold": m.threshold_value,
        "Breached": "Yes" if m.is_breached else "No"
    } for m in metric_list]


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
    options_list = list(system_names.keys())

    if "global_sys_id" in st.session_state and st.session_state.global_sys_id not in options_list:
        del st.session_state["global_sys_id"]

    def update_global_sys():
        st.session_state.global_sys_id = st.session_state.monitoring_sys_selector

    default_index = 0
    if "global_sys_id" in st.session_state:
        default_index = options_list.index(st.session_state.global_sys_id)

    selected_sys_id = st.selectbox(
        "Select AI System",
        options=options_list,
        index=default_index,
        format_func=lambda x: system_names[x],
        label_visibility="collapsed",
        key="monitoring_sys_selector",
        on_change=update_global_sys
    )
    if "global_sys_id" not in st.session_state:
        st.session_state.global_sys_id = selected_sys_id

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

        uploaded_file = st.file_uploader(" Choose a CSV file", type=["csv"], key=f"csv_uploader_{selected_sys_id}")

        if uploaded_file is not None:
            if st.button("Ingest CSV"):
                try:
                    result = ingest_metrics_from_csv(db, selected_sys_id, uploaded_file, current_user)

                    # Track which rows came from this specific upload so the
                    # "Recent Upload" tab shows only this batch. This gets
                    # overwritten on every new ingest, so the previous batch
                    # automatically falls into "Full History".
                    st.session_state[f"recent_ids_{selected_sys_id}"] = [
                        m.id for m in result["ingested"]
                    ]

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

        st.markdown('<p class="section-label">Metric Data</p>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Recent Upload", "Full History"])

        metrics = get_metrics(db, selected_sys_id)
        recent_ids = st.session_state.get(f"recent_ids_{selected_sys_id}", [])

        with tab1:
            recent_metrics = [m for m in metrics if m.id in recent_ids]
            if recent_metrics:
                render_metric_table(build_metric_data(recent_metrics))
                breached = [m for m in recent_metrics if m.is_breached]
                if breached:
                    st.error(f"{len(breached)} metric(s) breached threshold in this upload.")
                else:
                    st.success("No threshold breaches in this upload.")
            else:
                st.markdown(
                    '<p style="color:#7D9A7D;font-size:0.85rem;">No recent upload yet. Ingest a CSV to see it here.</p>',
                    unsafe_allow_html=True
                )

        with tab2:
            history_metrics = [m for m in metrics if m.id not in recent_ids]
            if history_metrics:
                render_metric_table(build_metric_data(history_metrics))
            else:
                st.markdown(
                    '<p style="color:#7D9A7D;font-size:0.85rem;">No historical data yet.</p>',
                    unsafe_allow_html=True
                )

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

        def format_to_ist(timestamp_str: str) -> str:
            try:
                # Replace 'Z' with UTC offset representation
                ts = timestamp_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ist_tz = timezone(timedelta(hours=5, minutes=30))
                dt_ist = dt.astimezone(ist_tz)
                return dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
            except Exception:
                return timestamp_str.split('T')[0]

        st.markdown('<p class="section-label">Audit Trail</p>', unsafe_allow_html=True)
        logs = get_audit_logs(db, selected_sys_id)
        if logs:
            for log in logs[:10]:
                formatted_time = format_to_ist(log.timestamp)
                with st.expander(f"{log.action} — {formatted_time}"):
                    st.markdown(f"<p style='color:#E6EDF3;font-size:0.85rem;'><strong>User:</strong> {log.user}</p>", unsafe_allow_html=True)
                    st.json(log.details)
        else:
            st.markdown('<p style="color:#7D9A7D;font-size:0.85rem;">No audit logs.</p>', unsafe_allow_html=True)


db.close()