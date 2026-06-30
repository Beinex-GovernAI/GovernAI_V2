from sqlalchemy.orm import Session
from database.models import RiskAssessment, RiskClassificationAnswer, AISystem
from services.audit_svc import log_action

# EU AI Act Risk Classification Questionnaire
#
# Each question carries a "weight" used for scoring, plus an optional
# trigger flag for answers that force an automatic tier regardless of the
# cumulative score:
#   - "prohibited_trigger": Article 5 prohibited practices (e.g. social
#     scoring, subliminal manipulation, real-time biometric ID by law
#     enforcement in public) -> forces tier to "Prohibited".
#   - "high_risk_trigger": Annex III high-risk use-cases (e.g. employment,
#     critical infrastructure, education, essential services, law
#     enforcement, migration/justice) -> forces tier to at least "High".
#
# Questions without either flag (e.g. transparency obligations under
# Article 50) only contribute to the cumulative score and do not force a
# tier on their own.
#
# Scoring model: every question whose answer matches its "risk_trigger"
# contributes its "weight" to a cumulative risk_score. If no hard trigger
# fires, the cumulative score is mapped to a tier via
# RISK_SCORE_THRESHOLDS.
RISK_QUESTIONS = [
    {
        "key": "q1_prohibited_practice",
        "text": "Does this system use subliminal, manipulative, or deceptive techniques, or perform social scoring of individuals by public authorities?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 10,
        "prohibited_trigger": "Yes"
    },
    {
        "key": "q2_biometric_realtime",
        "text": "Does this system perform real-time remote biometric identification in publicly accessible spaces for law enforcement purposes?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 9,
        "prohibited_trigger": "Yes"
    },
    {
        "key": "q3_biometric_categorization",
        "text": "Does this system perform biometric categorization or emotion recognition (e.g. in workplaces or educational institutions)?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 7,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q4_critical_infra",
        "text": "Is this system intended to be used as a safety component in the management of critical infrastructure (e.g. energy, water, transport)?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 8,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q5_education",
        "text": "Is this system used to determine access to, or to evaluate students in, education or vocational training institutions?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 7,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q6_employment",
        "text": "Is this system used for recruitment, task allocation, or performance/termination evaluation in an employment context?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 7,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q7_essential_services",
        "text": "Is this system used to evaluate creditworthiness, eligibility for public benefits, or insurance risk pricing for individuals?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 7,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q8_law_enforcement",
        "text": "Is this system used by or on behalf of law enforcement to assess risk of offending, evidence reliability, or profiling of individuals?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 8,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q9_migration_justice",
        "text": "Is this system used in migration, asylum, border control management, or to assist judicial authorities in interpreting facts/law?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 8,
        "high_risk_trigger": "Yes"
    },
    {
        "key": "q10_transparency",
        "text": "Does this system interact directly with natural persons, or generate synthetic audio/image/video/text content (e.g. chatbot, deepfake generator)?",
        "options": ["Yes", "No"],
        "risk_trigger": "Yes",
        "weight": 3
        # Article 50 transparency obligation only; contributes to score but
        # does not by itself force a High-risk tier.
    }
]

# Cumulative score thresholds used when no prohibited/high-risk trigger fires.
# Score is the sum of weights for every question whose answer matched its
# "risk_trigger". Checked highest-first.
RISK_SCORE_THRESHOLDS = [
    (15, "High"),     # score >= 15 -> treat as High even without a hard trigger
    (5, "Limited"),   # score >= 5  -> Limited risk (e.g. transparency-heavy systems)
    (0, "Minimal"),   # everything else
]


def _score_answers(answers: dict) -> int:
    """Sums the weights of every answer that matched its question's risk_trigger."""
    score = 0
    for q in RISK_QUESTIONS:
        if answers.get(q["key"]) == q.get("risk_trigger"):
            score += q.get("weight", 0)
    return score


def _tier_from_score(score: int) -> str:
    for threshold, tier in RISK_SCORE_THRESHOLDS:
        if score >= threshold:
            return tier
    return "Minimal"


def assess_risk(db: Session, system_id: str, answers: dict, current_user: str):
    """Evaluates risk questionnaire answers and assigns a tier using a
    weighted scoring mechanism, with hard overrides for prohibited
    practices (Article 5) and Annex III high-risk use-cases."""

    # 1. Check for prohibited practices first - hard override
    assigned_tier = None
    for q in RISK_QUESTIONS:
        if "prohibited_trigger" in q and answers.get(q["key"]) == q["prohibited_trigger"]:
            assigned_tier = "Prohibited"  # matches AISystem.risk_tier vocabulary used downstream
            break

    # 2. Check for Annex III high-risk triggers - hard override
    if assigned_tier is None:
        for q in RISK_QUESTIONS:
            if "high_risk_trigger" in q and answers.get(q["key"]) == q["high_risk_trigger"]:
                assigned_tier = "High"
                break

    # 3. Compute weighted score (used as the fallback tier driver, and
    #    stored alongside each answer for transparency/audit purposes)
    risk_score = _score_answers(answers)

    # 4. If no hard trigger fired, fall back to the score-based tier
    if assigned_tier is None:
        assigned_tier = _tier_from_score(risk_score)

    # 5. Additional logic: Check for PII in data sources (auto-raise risk floor)
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    tier_rank = {"Minimal": 0, "Limited": 1, "High": 2, "Prohibited": 3}
    if tier_rank[assigned_tier] < tier_rank["Limited"]:
        for ds in system.data_sources:
            if ds.contains_pii:
                assigned_tier = "Limited"  # Raise to at least limited if it has PII
                break

    # 6. Save Assessment
    assessment = RiskAssessment(
        system_id=system_id,
        calculated_tier=assigned_tier,
        assessed_by=current_user
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # 7. Save Answers (with each question's weight, for audit/traceability)
    weight_lookup = {q["key"]: q.get("weight", 0) for q in RISK_QUESTIONS}
    for key, val in answers.items():
        ans_record = RiskClassificationAnswer(
            assessment_id=assessment.id,
            question_key=key,
            answer=val,
            weight=weight_lookup.get(key, 0)
        )
        db.add(ans_record)

    # 8. Update System Tier
    system.risk_tier = assigned_tier
    db.commit()

    # 9. Log Action
    log_action(
        db,
        system_id,
        current_user,
        "TIER_ASSIGNED",
        {"assigned_tier": assigned_tier, "risk_score": risk_score}
    )

    return assessment
