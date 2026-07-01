import streamlit as st
from database.db import SessionLocal
from services.ai_system_svc import get_systems
from services.audit_svc import log_action
from services.risk_svc import RISK_QUESTIONS, assess_risk
from services.llm import (
    suggest_risk_tier,
    LLMRiskAssessmentError,
)

st.set_page_config(page_title="Risk Setup", page_icon="⚖️", layout="wide")

st.title("⚖️ Risk Classification Setup")

db = SessionLocal()
current_user = st.session_state.get("current_user", "Admin")

systems = get_systems(db)
if not systems:
    st.warning("No systems found. Please add a system in the Inventory first.")
else:
    # Select a system to assess
    system_names = {sys.id: sys.name for sys in systems}
    selected_sys_id = st.selectbox("Select AI System", options=list(system_names.keys()), format_func=lambda x: system_names[x])
    
    selected_sys = next(s for s in systems if s.id == selected_sys_id)
    
    st.subheader(f"Assess Risk for: {selected_sys.name}")
    st.write(f"**Current Risk Tier:** {selected_sys.risk_tier}")

    with st.expander("🤖 AI-Assisted Tier Suggestion (Beta)", expanded=False):
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
                        tier_colors = {
                            "Prohibited": "🔴",
                            "High": "🟠",
                            "Limited": "🟡",
                            "Minimal": "🟢",
                        }
                        dot = tier_colors.get(suggestion.internal_tier, "⚪")
                        st.success(
                            f"{dot} **Suggested Tier: {suggestion.eu_ai_act_label}** "
                            f"(GovernAI tier: `{suggestion.internal_tier}`)"
                        )
                        st.write(suggestion.explanation)
                        if suggestion.key_factors:
                            st.markdown("**Key factors identified:**")
                            for factor in suggestion.key_factors:
                                st.markdown(f"- {factor}")
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

    with st.form("risk_assessment_form"):
        st.write("Please answer the following questions based on EU AI Act criteria:")
        
        answers = {}
        for q in RISK_QUESTIONS:
            answers[q["key"]] = st.radio(q["text"], q["options"], key=q["key"])
            
        submitted = st.form_submit_button("Submit Assessment")
        
        if submitted:
            assessment = assess_risk(db, selected_sys_id, answers, current_user)
            st.success(f"Assessment completed. Assigned Tier: **{assessment.calculated_tier}**")
            st.rerun()

db.close()
