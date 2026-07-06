from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.db import Base, generate_uuid

def utcnow():
    return datetime.now(timezone.utc).isoformat()

class AISystem(Base):
    __tablename__ = "ai_systems"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    business_purpose = Column(String)
    model_vendor = Column(String)
    model_type = Column(String)  # (LLM, Classical ML, Computer Vision, Agentic AI)
    model_source = Column(String)  # (Open Source, Proprietary)
    agentic_trace_required = Column(String)  # (Yes, No)
    risk_tier = Column(String, default="Pending")  # (Prohibited, High, Limited, Minimal, Pending)
    compliance_status = Column(String, default="Pending")  # (Compliant, At Risk, Non-Compliant, Pending)
    created_at = Column(String, default=utcnow)
    updated_at = Column(String, default=utcnow, onupdate=utcnow)

    # Relationships
    data_sources = relationship("DataSource", back_populates="system", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="system", cascade="all, delete-orphan")
    compliance_records = relationship("ComplianceRecord", back_populates="system", cascade="all, delete-orphan")
    monitoring_metrics = relationship("MonitoringMetric", back_populates="system", cascade="all, delete-orphan")
    # Note: audit_logs intentionally has NO delete cascade — deleting a system
    # must not erase its compliance/audit history. See AuditLog.system_id below,
    # which is set to NULL (not deleted) via ondelete="SET NULL".
    audit_logs = relationship("AuditLog", back_populates="system")

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    system_id = Column(String(36), ForeignKey("ai_systems.id"))
    source_name = Column(String, nullable=False)
    description = Column(String)
    contains_pii = Column(Integer, default=0)  # 0 or 1
    pii_categories = Column(String)  # Comma-separated list

    system = relationship("AISystem", back_populates="data_sources")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    system_id = Column(String(36), ForeignKey("ai_systems.id"))
    calculated_tier = Column(String)
    assessed_by = Column(String)
    assessed_at = Column(String, default=utcnow)

    system = relationship("AISystem", back_populates="risk_assessments")
    answers = relationship("RiskClassificationAnswer", back_populates="assessment", cascade="all, delete-orphan")

class RiskClassificationAnswer(Base):
    __tablename__ = "risk_classification_answers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("risk_assessments.id"))
    question_key = Column(String, nullable=False)
    answer = Column(String)
    weight = Column(Float, default=0.0)

    assessment = relationship("RiskAssessment", back_populates="answers")

class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    system_id = Column(String(36), ForeignKey("ai_systems.id"))
    framework = Column(String, nullable=False)  # e.g., EU AI Act, NIST
    control_id = Column(String, nullable=False)
    control_description = Column(String)
    is_met = Column(Integer, default=0)  # 0 or 1
    evidence_link = Column(String)
    last_updated = Column(String, default=utcnow, onupdate=utcnow)

    system = relationship("AISystem", back_populates="compliance_records")

class MonitoringMetric(Base):
    __tablename__ = "monitoring_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    system_id = Column(String(36), ForeignKey("ai_systems.id"))
    metric_name = Column(String, nullable=False)  # (e.g., Drift, Bias, Hallucination, Cost)
    metric_value = Column(Float)
    threshold_value = Column(Float)
    is_breached = Column(Integer, default=0)  # 0 or 1
    timestamp = Column(String, default=utcnow)

    system = relationship("AISystem", back_populates="monitoring_metrics")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    system_id = Column(String(36), ForeignKey("ai_systems.id", ondelete="SET NULL"))
    user = Column(String)  # Who made the change
    action = Column(String, nullable=False)  # (e.g., STATUS_CHANGE, METRIC_BREACH, SYSTEM_CREATED)
    details = Column(String)  # JSON string containing old_value, new_value, or breach context
    timestamp = Column(String, default=utcnow)

    system = relationship("AISystem", back_populates="audit_logs")
    agent_traces = relationship("AgentActionTrace", back_populates="audit_log", cascade="all, delete-orphan")

class AgentActionTrace(Base):
    __tablename__ = "agent_action_trace"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    audit_log_id = Column(String(36), ForeignKey("audit_logs.id"))
    step_number = Column(Integer)
    action_taken = Column(String)
    tool_used = Column(String)
    decision_rationale = Column(String)

    audit_log = relationship("AuditLog", back_populates="agent_traces")