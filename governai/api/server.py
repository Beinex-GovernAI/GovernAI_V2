from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from database.db import get_db
from database.models import AISystem
from services.audit_svc import log_action
from services.llm.risk_suggester import suggest_risk_tier
from services.llm.exceptions import FoundryConnectionError, FoundryModelError, LLMResponseParseError
from api.schemas import SystemRegistrationRequest

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
    
    # 3. Log the system creation
    log_action(db, new_system.id, "API_INTEGRATION", "SYSTEM_CREATED", 
               {"risk_tier": new_system.risk_tier, "model_used": suggestion.model_used})
               
    return {
        "status": "success",
        "system_id": new_system.id,
        "risk_tier": new_system.risk_tier,
        "message": f"System registered and assigned {new_system.risk_tier} risk tier automatically."
    }
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from database.db import get_db
from database.models import AISystem
from services.audit_svc import log_action
from services.llm.risk_suggester import suggest_risk_tier
from services.llm.exceptions import FoundryConnectionError, FoundryModelError, LLMResponseParseError
from api.schemas import SystemRegistrationRequest, TelemetryPayload
from services.monitoring_svc import ingest_metric

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
    
    # 3. Log the system creation
    log_action(db, new_system.id, "API_INTEGRATION", "SYSTEM_CREATED", 
               {"risk_tier": new_system.risk_tier, "model_used": suggestion.model_used})
               
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