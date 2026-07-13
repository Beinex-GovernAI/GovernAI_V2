from sqlalchemy.orm import Session
from database.models import MonitoringMetric, AISystem
from services.ai_system_svc import update_status
from services.audit_svc import log_action
import pandas as pd 

DEFAULT_THRESHOLDS = {
    "Drift": 0.15,
    "Bias": 0.1,
    "Hallucination": 0.05,
    "Cost": 1000.0
}

def ingest_metric(db: Session, system_id: str, metric_name: str, metric_value: float, current_user: str):
    """Ingests a new metric reading, checks against thresholds, and updates state if breached."""
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    
    threshold = DEFAULT_THRESHOLDS.get(metric_name, 0.0)
    if system:
        if metric_name == "Drift" and system.drift_threshold is not None:
            threshold = system.drift_threshold
        elif metric_name == "Bias" and system.bias_threshold is not None:
            threshold = system.bias_threshold

    is_breached = 1 if metric_value > threshold else 0
    
    # 1. Save Metric
    new_metric = MonitoringMetric(
        system_id=system_id,
        metric_name=metric_name,
        metric_value=metric_value,
        threshold_value=threshold,
        is_breached=is_breached
    )
    db.add(new_metric)
    db.commit()
    db.refresh(new_metric)
    
    # 2. Trigger Cross-Wiring (The Golden Thread)
    if is_breached:
        system = db.query(AISystem).filter(AISystem.id == system_id).first()
        
        # Only log and update if we aren't already non-compliant
        if system and system.compliance_status != "Non-Compliant":
            reason = f"{metric_name} exceeded threshold: {metric_value} > {threshold}"
            
            # Log specific breach action
            log_action(db, system_id, "System Engine", "METRIC_BREACH", {
                "metric_name": metric_name,
                "metric_value": metric_value,
                "threshold": threshold,
                "triggering_user": current_user
            })
            
            # Update status
            update_status(db, system_id, "Non-Compliant", "System Engine", reason=reason)
            
    return new_metric

def ingest_metrics_from_csv(db: Session, system_id: str, csv_file, current_user: str):
    """
    Parses an uploaded CSV of metric readings and ingests each row using ingest_metric(),
    so threshold breach logic and audit logging still apply automatically per row.
    
    Expected CSV columns: metric_name, metric_value
    """
    try:
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        csv_file.seek(0)  # reset file pointer before retrying
        df = pd.read_csv(csv_file, encoding="utf-16")

    required_columns = {"metric_name", "metric_value"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_columns}. Found: {list(df.columns)}")

    results = []
    errors = []

    for index, row in df.iterrows():
        metric_name = str(row["metric_name"]).strip()
        try:
            metric_value = float(row["metric_value"])
        except (ValueError, TypeError):
            errors.append(f"Row {index + 2}: invalid metric_value '{row['metric_value']}'")
            continue

        if metric_name not in DEFAULT_THRESHOLDS:
            errors.append(f"Row {index + 2}: unknown metric_name '{metric_name}', skipped")
            continue

        new_metric = ingest_metric(db, system_id, metric_name, metric_value, current_user)
        results.append(new_metric)

    return {"ingested": results, "errors": errors, "total_rows": len(df)}

def get_metrics(db: Session, system_id: str, limit: int = 50):
    """Retrieves recent metrics for a system."""
    return db.query(MonitoringMetric).filter(MonitoringMetric.system_id == system_id).order_by(MonitoringMetric.timestamp.desc()).limit(limit).all()
