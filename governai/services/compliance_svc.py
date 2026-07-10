from sqlalchemy.orm import Session
from database.models import ComplianceRecord, AISystem
from services.audit_svc import log_action

EU_AI_ACT_CONTROLS = {
    "High": [
        {"id": "EU-ART-14", "desc": "Human Oversight: Implement measures for human intervention."},
        {"id": "EU-ART-15", "desc": "Accuracy, Robustness, Cybersecurity: Ensure high levels of resilience."},
        {"id": "EU-ART-11", "desc": "Technical Documentation: Maintain up-to-date documentation."},
        {"id": "EU-ART-17", "desc": "Quality Management System: Establish a QMS for the AI lifecycle."}
    ],
    "Limited": [
        {"id": "EU-ART-52", "desc": "Transparency: Inform users they are interacting with an AI system."}
    ],
    "Minimal": [
        {"id": "EU-ART-69", "desc": "Code of Conduct: Voluntary adherence to trustworthy AI practices."}
    ]
}

NIST_AI_RMF_CONTROLS = {
    "High": [
        {"id": "NIST-GOVERN-1.1", "desc": "Govern: Establish accountability structures and policies for AI risk management."},
        {"id": "NIST-MAP-1.1", "desc": "Map: Document the system's context, intended use, and impacted stakeholders."},
        {"id": "NIST-MEASURE-2.1", "desc": "Measure: Implement quantitative metrics to assess risks such as bias and robustness."},
        {"id": "NIST-MANAGE-1.1", "desc": "Manage: Establish a documented plan to respond to and mitigate identified AI risks."}
    ],
    "Limited": [
        {"id": "NIST-MAP-1.2", "desc": "Map: Communicate known system limitations and risks to relevant stakeholders."}
    ],
    "Minimal": [
        {"id": "NIST-GOVERN-1.2", "desc": "Govern: Maintain a basic inventory and documentation of the AI system."}
    ]
}

FRAMEWORK_CONTROLS = {
    "EU AI Act": EU_AI_ACT_CONTROLS,
    "NIST AI RMF": NIST_AI_RMF_CONTROLS
}

def generate_checklists(db: Session, system_id: str, frameworks: list = None):
    """
    Generates compliance records for the given system, based on its risk tier.
    By default generates checklists for ALL supported frameworks (EU AI Act + NIST AI RMF).
    Pass `frameworks=["NIST AI RMF"]` to generate only a specific one.
    """
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    if not system or system.risk_tier == "Pending":
        return []

    tier = system.risk_tier
    if tier == "Prohibited":
        return []

    if frameworks is None:
        frameworks = list(FRAMEWORK_CONTROLS.keys())

    existing = db.query(ComplianceRecord).filter(ComplianceRecord.system_id == system_id).all()
    existing_keys = {(r.framework, r.control_id) for r in existing}

    for framework_name in frameworks:
        controls = FRAMEWORK_CONTROLS.get(framework_name, {}).get(tier, [])
        for ctrl in controls:
            key = (framework_name, ctrl["id"])
            if key not in existing_keys:
                record = ComplianceRecord(
                    system_id=system_id,
                    framework=framework_name,
                    control_id=ctrl["id"],
                    control_description=ctrl["desc"]
                )
                db.add(record)
                existing_keys.add(key)

    db.commit()
    return db.query(ComplianceRecord).filter(ComplianceRecord.system_id == system_id).all()

def update_compliance_record(db: Session, record_id: str, is_met: int, evidence_link: str, updated_by: str = "System"):
    """Updates a single compliance control record and auto-updates system status."""
    from services.ai_system_svc import update_status

    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    if record:
        record.is_met = is_met
        record.evidence_link = evidence_link
        db.commit()

        log_action(
            db,
            system_id=record.system_id,
            user=updated_by,
            action="Compliance control updated",
            details={
                "control_id": record.control_id,
                "framework": record.framework,
                "is_met": bool(is_met),
                "evidence_link": evidence_link or None
            }
        )

        all_records = db.query(ComplianceRecord).filter(
            ComplianceRecord.system_id == record.system_id
        ).all()

        if all_records:
            all_met = all(r.is_met for r in all_records)
            any_unmet = any(not r.is_met for r in all_records)

            system = db.query(AISystem).filter(
                AISystem.id == record.system_id
            ).first()

            if system:
                if all_met:
                    update_status(db, record.system_id, "Compliant", "System Engine",
                                 reason="All compliance controls marked as met")
                elif any_unmet and system.compliance_status != "Non-Compliant":
                    update_status(db, record.system_id, "At Risk", "System Engine",
                                 reason="Some compliance controls remain unmet")

    return record

def get_compliance_score(db: Session, system_id: str, framework: str = None):
    """
    Calculates the percentage of met controls.
    If `framework` is given (e.g. "NIST AI RMF"), scores only that framework.
    If omitted, scores across ALL frameworks combined (preserves old behavior
    for callers like report_gen.py that don't pass a framework).
    """
    query = db.query(ComplianceRecord).filter(ComplianceRecord.system_id == system_id)
    if framework:
        query = query.filter(ComplianceRecord.framework == framework)
    records = query.all()

    if not records:
        return 0
    met_count = sum(1 for r in records if r.is_met)
    return int((met_count / len(records)) * 100)