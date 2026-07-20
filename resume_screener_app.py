import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="HR Resume Screener AI", page_icon="📄", layout="centered")

st.title("📄 HR Resume Screener AI")
st.markdown("Welcome to the automated resume screening portal. Paste a resume below to evaluate the candidate.")

# The GovernAI Backend API URL
GOVERNAI_INTAKE_URL = "http://localhost:8000/api/v1/scanner/intake"

resume_text = st.text_area("Candidate Resume Text", height=200, placeholder="Paste resume here...")

if st.button("Screen Candidate", type="primary"):
    if not resume_text:
        st.error("Please enter a resume.")
    else:
        with st.spinner("Analyzing resume using LangChain Agent..."):
            # Simulate LLM Processing Delay
            time.sleep(1.5)
            
            # Simulated LangChain Logic
            if "Python" in resume_text and "AWS" in resume_text:
                decision = "Shortlisted"
                score = 0.85
                st.success(f"**Decision:** {decision} (Confidence: {score})")
            else:
                decision = "Rejected"
                score = 0.40
                st.error(f"**Decision:** {decision} (Confidence: {score})")
                
            st.divider()
            st.info("Sending telemetry to GovernAI in the background...")
            
            # Prepare payload for GovernAI generic scanner endpoint
            scanner_payload = {
                "system_metadata": {
                    "name": "HR Resume Screener AI",
                    "owner": "HR Dept",
                    "business_purpose": "Automatically screens incoming resumes and ranks them based on job description fit.",
                    "model_type": "LangChain Agent",
                    "model_vendor": "OpenAI",
                    "model_source": "Proprietary API",
                },
                "compliance_evidence": {
                    "documentation_url": "https://wiki.beinex.com/hr-ai-screener"
                },
                "raw_prediction": {
                    "input_text": resume_text,
                    "output_text": decision,
                    "confidence_score": score
                }
            }
            
            # Background API Call to GovernAI Intake Endpoint
            try:
                resp = requests.post(GOVERNAI_INTAKE_URL, json=scanner_payload, timeout=5)
                if resp.status_code == 200:
                    gov_data = resp.json()
                    st.toast(f"GovernAI Logged! Status: {gov_data.get('compliance_status')}", icon="🛡️")
                else:
                    st.warning(f"GovernAI API Error: {resp.status_code}")
            except Exception as e:
                st.error("Failed to reach GovernAI backend. Ensure the FastAPI server is running.")

st.markdown("---")
st.caption("Powered by LangChain & OpenAI | Monitored by GovernAI")
