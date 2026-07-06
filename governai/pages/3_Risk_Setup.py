import streamlit as st
import os
from database.db import SessionLocal
from database.models import RiskAssessment
from services.ai_system_svc import get_systems
from services.audit_svc import log_action
from services.risk_svc import RISK_QUESTIONS, assess_risk
from services.llm import (
    suggest_risk_tier,
    LLMRiskAssessmentError,
)

st.set_page_config(page_title="Risk Setup", page_icon="⚖️", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

st.title("Risk Classification Setup")

db = SessionLocal()
current_user = st.session_state.get("current_user", "Admin")

systems = get_systems(db)
if not systems:
    st.warning("No systems found. Please add a system in the Inventory first.")
else:
    st.markdown('<p class="section-label">Select System</p>', unsafe_allow_html=True)

    system_names = {sys.id: sys.name for sys in systems}
    options_list = list(system_names.keys())

    if "global_sys_id" in st.session_state and st.session_state.global_sys_id not in options_list:
        del st.session_state["global_sys_id"]

    def update_global_sys():
        st.session_state.global_sys_id = st.session_state.risk_setup_sys_selector

    default_index = 0
    if "global_sys_id" in st.session_state:
        default_index = options_list.index(st.session_state.global_sys_id)

    selected_sys_id = st.selectbox(
        "Select AI System",
        options=options_list,
        index=default_index,
        format_func=lambda x: system_names[x],
        label_visibility="collapsed",
        key="risk_setup_sys_selector",
        on_change=update_global_sys
    )
    if "global_sys_id" not in st.session_state:
        st.session_state.global_sys_id = selected_sys_id

    selected_sys = next(s for s in systems if s.id == selected_sys_id)

    tier = selected_sys.risk_tier or "Pending"
    tier_class = {
        "High": "tier-high",
        "Limited": "tier-limited",
        "Minimal": "tier-minimal",
        "Pending": "tier-pending",
        "Prohibited": "tier-high",
    }.get(tier, "tier-pending")

    # Header card — mirrors the gov-card pattern used elsewhere
    st.markdown(f"""
    <div class="gov-card">
        <div class="gov-card-title">{selected_sys.name}</div>
        <div class="gov-card-sub">{selected_sys.owner or 'No owner set'}</div>
        <div style="margin-top:0.6rem;">
            <span style="color:#7D9A7D;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">Current Risk Tier&nbsp;&nbsp;</span>
            <span class="{tier_class}">{tier}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # LLM-assisted suggestion
    with st.expander("AI-Assisted Tier Suggestion (Beta)", expanded=False):
        st.caption(
            "Describe the system in plain language and a local LLM (via Foundry Local) "
            "will suggest a likely EU AI Act tier with an explanation. This is advisory "
            "only -- it does not save anything and does not replace the questionnaire below."
        )
        description = st.text_area(
            "Plain-language system description",
            placeholder=(
                "e.g. 'An internal tool that screens incoming resumes and ranks "
                "candidates before a recruiter reviews them.'"
            ),
            key="llm_risk_description",
        )

        if st.button("Suggest Risk Tier", key="llm_suggest_btn"):
            if not description or not description.strip():
                st.warning("Please enter a system description first.")
            else:
                with st.spinner("Asking the local model..."):
                    try:
                        suggestion = suggest_risk_tier(description)
                    except LLMRiskAssessmentError as e:
                        st.error(f"Couldn't generate a suggestion: {e}")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")
                    else:
                        suggested_class = {
                            "High": "tier-high",
                            "Limited": "tier-limited",
                            "Minimal": "tier-minimal",
                            "Prohibited": "tier-high",
                        }.get(suggestion.internal_tier, "tier-pending")

                        st.markdown(f"""
                        <div class="gov-card" style="margin-top:0.75rem;">
                            <div style="margin-bottom:0.5rem;">
                                <span style="color:#7D9A7D;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">Suggested Tier&nbsp;&nbsp;</span>
                                <span class="{suggested_class}">{suggestion.eu_ai_act_label}</span>
                            </div>
                            <p style="color:#E6EDF3;font-size:0.88rem;margin:0.4rem 0;">{suggestion.explanation}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        if suggestion.key_factors:
                            st.markdown('<p class="section-label" style="margin-top:0.75rem;">Key Factors</p>', unsafe_allow_html=True)
                            for factor in suggestion.key_factors:
                                st.markdown(f"<div style='color:#E6EDF3;font-size:0.85rem;padding:0.15rem 0;'>• {factor}</div>", unsafe_allow_html=True)

                        st.caption(
                            f"Model: `{suggestion.model_used}` · "
                            f"Endpoint discovery: `{suggestion.discovery_mode}`"
                        )

                        log_action(
                            db,
                            selected_sys_id,
                            current_user,
                            "LLM_RISK_SUGGESTION",
                            {
                                "description": description,
                                "suggested_tier": suggestion.internal_tier,
                                "eu_ai_act_label": suggestion.eu_ai_act_label,
                                "model_used": suggestion.model_used,
                            },
                        )

    st.markdown("---")
    st.markdown('<p class="section-label">Risk Assessment Questionnaire</p>', unsafe_allow_html=True)

    with st.form("risk_assessment_form"):
        st.markdown(
            "<p style='color:#7D9A7D;font-size:0.85rem;margin-bottom:1rem;'>Please answer the following questions based on EU AI Act criteria:</p>",
            unsafe_allow_html=True,
        )

        latest_assessment = db.query(RiskAssessment).filter(RiskAssessment.system_id == selected_sys_id).order_by(RiskAssessment.assessed_at.desc()).first()
        previous_answers = {}
        if latest_assessment:
            for ans in latest_assessment.answers:
                previous_answers[ans.question_key] = ans.answer

        answers = {}
        for q in RISK_QUESTIONS:
            prev_ans = previous_answers.get(q["key"])
            try:
                default_index = q["options"].index(prev_ans) if prev_ans else 0
            except ValueError:
                default_index = 0
                
            # Make the widget key unique per system so session state doesn't overlap
            widget_key = f"{selected_sys_id}_{q['key']}"
            answers[q["key"]] = st.radio(q["text"], q["options"], index=default_index, key=widget_key)

        submitted = st.form_submit_button("Submit Assessment")

        if submitted:
            assessment = assess_risk(db, selected_sys_id, answers, current_user)
            st.success(f"Assessment completed. Assigned Tier: **{assessment.calculated_tier}**")
            st.rerun()

db.close()