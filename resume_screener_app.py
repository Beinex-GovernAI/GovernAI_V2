import streamlit as st
import os
import sys
import requests
import json
import time

# Path setup so we can import from governai
sys.path.append(os.path.join(os.path.dirname(__file__), 'governai'))

from dotenv import load_dotenv
load_dotenv()

GOVERNAI_INTAKE_URL = os.environ.get("GOVERNAI_INTAKE_URL", "http://localhost:8000/api/v1/scanner/intake")
KIJI_PROXY_URL = os.environ.get("KIJI_PROXY_URL", "http://localhost:8080/api/pii/check")

st.set_page_config(page_title="HR Resume Screener AI", page_icon="📄", layout="centered")

st.title("📄 HR Resume Screener AI")
st.caption("Upload a candidate's resume and let the AI evaluate their fit.")

st.divider()

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])

def extract_text(file):
    if file.name.endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return str(file.read(), "utf-8")

def screen_with_llm(text: str) -> dict:
    """Evaluate resume with OpenAI or fall back to keyword rules."""
    prompt = f"""You are an AI recruitment assistant. Evaluate this resume for a Python Backend Engineer role.
Requirements: Python, SQL, REST APIs, Git, AWS.

Output ONLY valid JSON in this format:
{{"decision": "Shortlisted" or "Rejected", "score": <0.0-1.0>, "justification": "<short reason>"}}

Resume:
{text[:3000]}"""

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                timeout=15
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            pass

    # Keyword fallback
    skills = ["python", "sql", "aws", "git", "api", "rest"]
    matches = [s for s in skills if s in text.lower()]
    score = round(len(matches) / len(skills), 2)
    return {
        "decision": "Shortlisted" if score >= 0.5 else "Rejected",
        "score": score,
        "justification": f"Matched {len(matches)}/{len(skills)} required skills: {', '.join(matches) or 'none'}."
    }

if uploaded_file:
    resume_text = extract_text(uploaded_file)
    st.success(f"✅ Resume loaded: **{uploaded_file.name}** ({len(resume_text)} characters)")

    if st.button("Evaluate Candidate", type="primary"):

        # Step 1: Kiji PII masking
        masked_text = resume_text
        kiji_active = False
        with st.spinner("Step 1/3 — Running PII masking..."):
            try:
                resp = requests.post(KIJI_PROXY_URL, json={"message": resume_text}, timeout=3)
                if resp.status_code == 200:
                    masked_text = resp.json().get("masked_message", resume_text)
                    kiji_active = True
            except Exception:
                pass

        if kiji_active:
            st.info("🔒 Kiji PII Proxy active — candidate data redacted before LLM call.")
        else:
            st.warning("⚠️ Kiji offline — sending without PII masking.")

        # Step 2: LLM Screening
        with st.spinner("Step 2/3 — Evaluating with AI..."):
            time.sleep(0.5)
            result = screen_with_llm(masked_text)

        decision = result.get("decision", "Rejected")
        score = result.get("score", 0.0)
        justification = result.get("justification", "")

        st.divider()
        if decision == "Shortlisted":
            st.success(f"## ✅ Decision: {decision}")
        else:
            st.error(f"## ❌ Decision: {decision}")

        col1, col2 = st.columns(2)
        col1.metric("Skill Match Score", f"{int(score * 100)}%")
        col2.metric("Kiji PII Masking", "Active ✅" if kiji_active else "Offline ⚠️")
        st.markdown(f"**AI Justification:** {justification}")

        # Step 3: GovernAI Telemetry
        with st.spinner("Step 3/3 — Logging to GovernAI..."):
            payload = {
                "system_metadata": {
                    "name": "HR Resume Screener AI",
                    "owner": "HR Dept",
                    "business_purpose": "Automatically screens incoming resumes and ranks candidates by job fit.",
                    "model_type": "LLM Agent",
                    "model_vendor": "OpenAI",
                    "model_source": "GPT-4o-mini",
                },
                "compliance_evidence": {
                    "documentation_url": "https://wiki.beinex.com/hr-ai-screener",
                    "human_in_loop": True,
                    "privacy_filters": kiji_active
                },
                "raw_prediction": {
                    "input_text": masked_text[:2000],
                    "output_text": decision,
                    "confidence_score": score
                }
            }
            try:
                gov_resp = requests.post(GOVERNAI_INTAKE_URL, json=payload, timeout=5)
                if gov_resp.status_code == 200:
                    data = gov_resp.json()
                    st.success(f"🛡️ GovernAI logged this evaluation. System compliance status: **{data.get('compliance_status')}**")
                else:
                    st.error(f"GovernAI error {gov_resp.status_code}: {gov_resp.text}")
            except Exception as e:
                st.error(f"Could not reach GovernAI backend: {e}")

st.divider()
st.caption("Monitored by GovernAI | PII Protected by Kiji Privacy Proxy")
