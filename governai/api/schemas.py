from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class SystemRegistrationRequest(BaseModel):
    """Payload for POST /api/v1/systems/register"""
    name: str
    owner: str
    business_purpose: str
    model_type: str
    model_vendor: Optional[str] = None
    model_source: Optional[str] = None
    drift_threshold: Optional[float] = None
    bias_threshold: Optional[float] = None


class MetricPayload(BaseModel):
    """A single telemetry metric reading."""
    name: str
    value: float


class TelemetryPayload(BaseModel):
    """Payload for POST /api/v1/systems/{system_id}/telemetry"""
    metrics: List[MetricPayload]

class RawPredictionPayload(BaseModel):
    input_text: Optional[str] = None
    output_text: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class SystemMetadataPayload(BaseModel):
    name: str
    owner: str
    business_purpose: str
    model_type: str
    model_vendor: Optional[str] = None
    model_source: Optional[str] = None

class ScannerPayload(BaseModel):
    """Payload for POST /api/v1/scanner/intake"""
    system_metadata: SystemMetadataPayload
    compliance_evidence: Optional[Dict[str, Any]] = None
    raw_prediction: Optional[RawPredictionPayload] = None