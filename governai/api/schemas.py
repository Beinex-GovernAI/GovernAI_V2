from typing import List, Optional
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