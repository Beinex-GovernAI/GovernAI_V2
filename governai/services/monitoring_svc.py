import streamlit as st
import pandas as pd
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.monitoring_svc import DEFAULT_THRESHOLDS, ingest_metrics_from_csv, get_metrics
from services.audit_svc import get_audit_logs

st.set_page_config(page_title="Monitoring", page_icon="", layout="wide")

def load_css():
    import os
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title("System Monitoring & Alerts")

db = SessionLocal()
current_user = st.session_state.get("current_user", "Admin")

systems = get_systems(db)

if not systems:
    st.warning("No systems found.")
else:
    system_names = {sys.id: sys.name for sys in systems}
    selected_sys_id = st.selectbox(
        "Select System",
        options=list(system_names.keys()),
        format_func=lambda x: system_names[x]
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
        <div style='background:#0D2D0D;border:1px solid #1A3A1A;border-radius:6px;
        padding:0.75rem 1rem;margin-bottom:1rem'>
            <p style='color:#7D9A7D;font-size:0.72rem;text-transform:uppercase;
            letter-spacing:0.5px;margin:0 0 0.25rem 0'>Supported Metrics & Thresholds</p>
            <p style='color:#E6EDF3;font-size:0.85rem;margin:0'>{DEFAULT_THRESHOLDS}</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file is not None:
            if st.button("Ingest CSV"):
                try:
                    result = ingest_metrics_from_csv(
                        db, selected_sys_id, uploaded_file, current_user
                    )
                    # Store ingested metric IDs in session state for "Recent" tab
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

# Tabs for Recent vs History
st.markdown('<p class="section-label">Metric Data</p>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["Recent Upload", "Full History"])

all_metrics = get_metrics(db, selected_sys_id)

# "Recent" = the exact rows from the last CSV you just ingested this session.
# Everything else (including older uploads) goes to Full History.
recent_ids = st.session_state.get(f"recent_ids_{selected_sys_id}", [])

with tab1:
    recent_metrics = [m for m in all_metrics if m.id in recent_ids]
    if recent_metrics:
        recent_data = [{
            "Timestamp": m.timestamp,
            "Metric": m.metric_name,
            "Value": m.metric_value,
            "Threshold": m.threshold_value,
            "Breached": "YES" if m.is_breached else "NO"
        } for m in recent_metrics]
        df = pd.DataFrame(recent_data)
        st.dataframe(df, use_container_width=True)
        breached = [m for m in recent_metrics if m.is_breached]
        if breached:
            st.error(f"{len(breached)} metric(s) breached threshold in this upload.")
        else:
            st.success("No threshold breaches in this upload.")
    else:
        st.info("No metrics ingested in the last 10 minutes.")

with tab2:
    history_metrics = [m for m in all_metrics if m.id not in recent_ids]
    if history_metrics:
        history_data = [{
            "Timestamp": m.timestamp,
            "Metric": m.metric_name,
            "Value": m.metric_value,
            "Threshold": m.threshold_value,
            "Breached": "YES" if m.is_breached else "NO"
        } for m in history_metrics]
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("No historical data yet.")

db.close()