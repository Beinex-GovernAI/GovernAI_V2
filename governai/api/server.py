from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from database.db import get_db
from database.models import AISystem
from database.models import utcnow  
from services.audit_svc import log_action
from services.llm.risk_suggester import suggest_risk_tier
from services.llm.exceptions import FoundryConnectionError, FoundryModelError, LLMResponseParseError
from api.schemas import SystemRegistrationRequest, TelemetryPayload, ScannerPayload
from services.monitoring_svc import ingest_metric
from services.compliance_svc import generate_checklists, auto_populate_compliance
from services.analytics_svc import save_raw_prediction, calculate_batch_drift, calculate_batch_bias

app = FastAPI(
    title="GovernAI Integration API",
    description="API for integrating real AI systems with GovernAI for automated risk assessment and telemetry tracking.",
    version="1.0.0"
)

# Allow all origins for the presentation phase
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "GovernAI Integration API is running"}

@app.post("/api/v1/systems/register")
def register_system(request: SystemRegistrationRequest, db: Session = Depends(get_db)):
    try:
        # 1. Suggest Risk Tier using LLM & Kiji
        suggestion = suggest_risk_tier(request.business_purpose)
    except (FoundryConnectionError, FoundryModelError, LLMResponseParseError) as e:
        raise HTTPException(status_code=503, detail=f"LLM Risk Assessment failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # 2. Create the System in the DB
    new_system = AISystem(
        name=request.name,
        owner=request.owner,
        business_purpose=request.business_purpose,
        model_type=request.model_type,
        model_vendor=request.model_vendor,
        model_source=request.model_source,
        risk_tier=suggestion.internal_tier,
        drift_threshold=request.drift_threshold,
        bias_threshold=request.bias_threshold
    )
    db.add(new_system)
    db.commit()
    db.refresh(new_system)
    
    # 2.5. Generate compliance checklists based on risk tier
    generate_checklists(db, new_system.id)
    
    # 3. Log the system creation
    log_action(db, new_system.id, "API_INTEGRATION", "SYSTEM_CREATED", 
               {"risk_tier": new_system.risk_tier, "model_used": suggestion.model_used})

    # 3b. If the risk tier came from the OpenAI fallback (Foundry Local was
    # unreachable or OOM'd) rather than the local model, record that
    # separately — auditors/Mebin can then see exactly which systems were
    # assessed locally vs. via the cloud fallback.
    if suggestion.discovery_mode == "openai-fallback":
        log_action(db, new_system.id, "API_INTEGRATION", "FALLBACK_TO_OPENAI",
                   {"reason": "Foundry Local unreachable or OOM",
                    "model_used": suggestion.model_used})
               
    return {
        "status": "success",
        "system_id": new_system.id,
        "risk_tier": new_system.risk_tier,
        "message": f"System registered and assigned {new_system.risk_tier} risk tier automatically."
    }

@app.post("/api/v1/systems/{system_id}/telemetry")
def ingest_telemetry(system_id: str, payload: TelemetryPayload, db: Session = Depends(get_db)):
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"AI system {system_id} not found")

    ingested = []
    for metric in payload.metrics:
        result = ingest_metric(
            db,
            system_id=system_id,
            metric_name=metric.name,
            metric_value=metric.value,
            current_user="integration_api",
        )
        ingested.append({
            "metric_name": result.metric_name,
            "metric_value": result.metric_value,
            "threshold_value": result.threshold_value,
            "is_breached": bool(result.is_breached),
        })

    db.refresh(system)
    return {
        "system_id": system.id,
        "compliance_status": system.compliance_status,
        "metrics_ingested": ingested,
    }

@app.post("/api/v1/scanner/intake")
def scanner_intake(payload: ScannerPayload, db: Session = Depends(get_db)):
    # 1. Lookup or create system
    system = db.query(AISystem).filter(AISystem.name == payload.system_metadata.name).first()
    
    if not system:
        try:
            suggestion = suggest_risk_tier(payload.system_metadata.business_purpose)
        except Exception:
            # Fallback if LLM fails
            suggestion = type("obj", (object,), {"internal_tier": "Pending", "model_used": "Fallback"})
            
        system = AISystem(
            name=payload.system_metadata.name,
            owner=payload.system_metadata.owner,
            business_purpose=payload.system_metadata.business_purpose,
            model_type=payload.system_metadata.model_type,
            model_vendor=payload.system_metadata.model_vendor,
            model_source=payload.system_metadata.model_source,
            risk_tier=suggestion.internal_tier,
            drift_threshold=0.15,
            bias_threshold=0.10
        )
        db.add(system)
        db.commit()
        db.refresh(system)
        
        generate_checklists(db, system.id)
        log_action(db, system.id, "API_INTEGRATION", "SYSTEM_AUTO_REGISTERED", {"risk_tier": system.risk_tier})
        
   # 2. Process Raw Predictions (Analytics) — now batch-based over the last N
    if payload.raw_prediction:
        save_raw_prediction(db, system.id, payload.raw_prediction)
        drift_val = calculate_batch_drift(db, system.id)
        bias_val = calculate_batch_bias(db, system.id)

        ingest_metric(db, system.id, "Drift", drift_val, current_user="scanner_integration")
        ingest_metric(db, system.id, "Bias", bias_val, current_user="scanner_integration") 
    # 3. Process Compliance Evidence
    if payload.compliance_evidence:
        auto_populate_compliance(db, system.id, payload.compliance_evidence, "scanner_integration")
        
    db.refresh(system)
    return {
        "status": "success",
        "system_id": system.id,
        "compliance_status": system.compliance_status
    }
@app.post("/api/v1/systems/{system_id}/heartbeat")
def system_heartbeat(system_id: str, db: Session = Depends(get_db)):
    """
    Lightweight liveness ping. Updates AISystem.updated_at only -- does NOT
    run compliance checks, does NOT log drift/bias metrics, does NOT write
    an audit log entry. Purpose is purely to show a system is still being
    monitored between real evaluations, without polluting compliance or
    monitoring data with fake events.
    """
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"AI system {system_id} not found")

    system.updated_at = utcnow()
    db.commit()
    db.refresh(system)

    return {
        "system_id": system.id,
        "status": "alive",
        "last_seen": system.updated_at
    }