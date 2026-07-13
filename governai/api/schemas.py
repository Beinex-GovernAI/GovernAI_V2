from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SystemRegistrationRequest(BaseModel):
    name: str = Field(..., description="Name of the AI system")
    owner: str = Field(..., description="Owner or team responsible")
    business_purpose: str = Field(..., description="Description of what the AI does")
    model_type: Optional[str] = Field("LLM", description="Type of the model (e.g. LLM, Computer Vision)")
    model_vendor: Optional[str] = Field("Custom", description="Vendor of the model")
    model_source: Optional[str] = Field("Internal", description="Open Source or Proprietary")
    drift_threshold: Optional[float] = Field(0.1, description="Threshold for drift metric")
    bias_threshold: Optional[float] = Field(0.1, description="Threshold for bias metric")

class TelemetryMetric(BaseModel):
    name: str = Field(..., description="Metric name (e.g., Drift, Bias)")
    value: float = Field(..., description="Current value of the metric")

class TelemetryPayload(BaseModel):
    metrics: List[TelemetryMetric] = Field(..., description="List of metrics to report")
