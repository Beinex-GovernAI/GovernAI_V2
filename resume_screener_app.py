import streamlit as st
import os
import sys
import requests
import json
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

# Path setup so we can import from governai
sys.path.append(os.path.join(os.path.dirname(__file__), 'governai'))

from dotenv import load_dotenv
load_dotenv()

GOVERNAI_BASE_URL = os.environ.get("GOVERNAI_BASE_URL", "http://localhost:8000")
GOVERNAI_INTAKE_URL = os.environ.get("GOVERNAI_INTAKE_URL", f"{GOVERNAI_BASE_URL}/api/v1/scanner/intake")
KIJI_PROXY_URL = os.environ.get("KIJI_PROXY_URL", "http://localhost:8080/api/pii/check")
HEARTBEAT_INTERVAL_MINUTES = int(os.environ.get("GOVERNAI_HEARTBEAT_MINUTES", "5"))

st.set_page_config(page_title="HR Resume Screener AI", page_icon="📄", layout="centered")

st.title("📄 HR Resume Screener AI")
st.caption("Upload a candidate's resume and let the AI evaluate their fit.")


# --- Periodic Heartbeat ---
# Registers this app as a system with GovernAI once (no raw_prediction, so no
# fake drift/bias gets logged), then starts a background job that pings
# /heartbeat every N minutes for as long as the app is open. This lets
# GovernAI show the system as continuously monitored, not just active when
# someone actually evaluates a resume.
#
# @st.cache_resource ensures this only runs ONCE per server process, even
# though Streamlit re-runs this whole script on every widget interaction.
@st.cache_resource
def register_system_and_start_heartbeat():
    system_id = None
    try:
        resp = requests.post(GOVERNAI_INTAKE_URL, json={
            "system_metadata": {
                "name": "HR Resume Screener AI",
                "owner": "HR Dept",
                "business_purpose": "Automatically screens incoming resumes and ranks candidates by job fit.",
                "model_type": "LLM Agent",
                "model_vendor": "OpenAI",
                "model_source": "GPT-4o-mini",
            }
        }, timeout=5)
        if resp.status_code == 200:
            system_id = resp.json().get("system_id")
    except Exception as e:
        print(f"[heartbeat] Could not register system with GovernAI: {e}")
        return None

    if not system_id:
        return None

    def send_heartbeat():
        try:
            url = f"{GOVERNAI_BASE_URL}/api/v1/systems/{system_id}/heartbeat"
            requests.post(url, timeout=5)
        except Exception as e:
            print(f"[heartbeat] Failed to send heartbeat: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_heartbeat, "interval", minutes=HEARTBEAT_INTERVAL_MINUTES)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))

    return system_id


_heartbeat_system_id = register_system_and_start_heartbeat()

if _heartbeat_system_id:
    st.caption(f"🟢 Monitored system ID `{_heartbeat_system_id[:8]}...` — heartbeat every {HEARTBEAT_INTERVAL_MINUTES} min")
else:
    st.caption("🔴 Could not register with GovernAI — heartbeat inactive")

st.divider()

# --- Job Profiles ---
# Each profile drives both the prompt sent to the LLM and the keyword fallback,
# so the demo can visibly show role-specific governance (different skill sets,
# different risk framing) rather than one hardcoded role.
JOB_PROFILES = {
    "Python Backend Engineer": {
        "requirements": "Python, SQL, REST APIs, Git, AWS",
        "skills": ["python", "sql", "aws", "git", "api", "rest"],
    },
    "AI Research Scientist": {
        "requirements": "Python, PyTorch/TensorFlow, research publications, statistics, experiment design",
        "skills": ["python", "pytorch", "tensorflow", "research", "statistics", "machine learning"],
    },
    "Frontend Developer": {
        "requirements": "JavaScript, React, HTML/CSS, UI/UX principles, accessibility",
        "skills": ["javascript", "react", "html", "css", "ui", "accessibility"],
    },
    "Data Analyst": {
        "requirements": "SQL, Excel, data visualization, statistics, Python or R",
        "skills": ["sql", "excel", "tableau", "statistics", "python", "r"],
    },
}

# --- Job Profile Selection ---
selected_role = st.selectbox("Select Job Profile", list(JOB_PROFILES.keys()))
role_requirements = JOB_PROFILES[selected_role]["requirements"]
role_skills = JOB_PROFILES[selected_role]["skills"]

st.caption(f"**Requirements for {selected_role}:** {role_requirements}")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])

def extract_text(file):
    if file.name.endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return str(file.read(), "utf-8")

def screen_with_llm(text: str, role: str, requirements: str, skills: list) -> dict:
    """Evaluate resume with OpenAI or fall back to keyword rules."""
    prompt = f"""You are an AI recruitment assistant. Evaluate this resume for a {role} role.
Requirements: {requirements}.

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

    # Keyword fallback, using the selected role's skill list
    matches = [s for s in skills if s in text.lower()]
    score = round(len(matches) / len(skills), 2) if skills else 0.0
    return {
        "decision": "Shortlisted" if score >= 0.5 else "Rejected",
        "score": score,
        "justification": f"Matched {len(matches)}/{len(skills)} required skills for {role}: {', '.join(matches) or 'none'}."
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
        with st.spinner(f"Step 2/3 — Evaluating for {selected_role}..."):
            time.sleep(0.5)
            result = screen_with_llm(masked_text, selected_role, role_requirements, role_skills)

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
        st.markdown(f"**Role Evaluated:** {selected_role}")
        st.markdown(f"**AI Justification:** {justification}")

        # Step 3: GovernAI Telemetry
        with st.spinner("Step 3/3 — Logging to GovernAI..."):
            payload = {
                "system_metadata": {
                    "name": "HR Resume Screener AI",
                    "owner": "HR Dept",
                    "business_purpose": f"Automatically screens incoming resumes for the {selected_role} role and ranks candidates by job fit.",
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
                gov_resp = requests.post(GOVERNAI_INTAKE_URL, json=payload, timeout=30)
                if gov_resp.status_code == 200:

                    data = gov_resp.json()
                    st.success(f"🛡️ GovernAI logged this evaluation. System compliance status: **{data.get('compliance_status')}**")
                else:
                    st.error(f"GovernAI error {gov_resp.status_code}: {gov_resp.text}")
            except Exception as e:
                st.error(f"Could not reach GovernAI backend: {e}")

st.divider()
st.caption("Monitored by GovernAI | PII Protected by Kiji Privacy Proxy")