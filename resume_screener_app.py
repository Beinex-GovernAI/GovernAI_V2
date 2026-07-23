import streamlit as st
import os
import sys
import requests
import json
import time
import atexit
import base64
from apscheduler.schedulers.background import BackgroundScheduler

# Path setup so we can import from governai
sys.path.append(os.path.join(os.path.dirname(__file__), 'governai'))

from dotenv import load_dotenv
load_dotenv()

GOVERNAI_BASE_URL = os.environ.get("GOVERNAI_BASE_URL", "http://localhost:8000")
GOVERNAI_INTAKE_URL = os.environ.get("GOVERNAI_INTAKE_URL", f"{GOVERNAI_BASE_URL}/api/v1/scanner/intake")
HEARTBEAT_INTERVAL_MINUTES = int(os.environ.get("GOVERNAI_HEARTBEAT_MINUTES", "5"))

st.set_page_config(page_title="HR Resume Screener AI", page_icon="📄", layout="centered")

st.title("📄 HR Resume Screener AI")
st.caption("Upload a candidate's resume (PDF, TXT, or Image) and let the AI evaluate their fit.")

# --- Periodic Heartbeat ---
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
uploaded_file = st.file_uploader("Upload Resume (PDF, TXT, or Image)", type=["pdf", "txt", "png", "jpg", "jpeg"])

def extract_text(file):
    if file.name.endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return str(file.read(), "utf-8")

def screen_with_llm(text: str, role: str, requirements: str, skills: list) -> dict:
    """Evaluate resume text with OpenAI or fall back to keyword rules."""
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
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content)
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

def screen_image_with_llm(image_bytes: bytes, mime_type: str, role: str, requirements: str, skills: list) -> dict:
    """Evaluate image resume with OpenAI using multimodal input."""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    prompt = f"""You are an AI recruitment assistant. You will be provided with an image of a resume.
Evaluate this resume for a {role} role based on these requirements: {requirements}.

First, transcribe the resume content accurately. Then determine the fit.

Output ONLY valid JSON in this format:
{{
  "transcription": "<full text of the resume extracted from the image>",
  "decision": "Shortlisted" or "Rejected",
  "score": <0.0-1.0>,
  "justification": "<short reason>"
}}"""

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                timeout=25
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content)
        except Exception as e:
            print(f"Error in image evaluation: {e}")
            pass

    return {
        "transcription": "Image uploaded, but API key missing or call failed.",
        "decision": "Rejected",
        "score": 0.0,
        "justification": "Could not evaluate image resume because OpenAI API key is missing or the request timed out."
    }

if uploaded_file:
    is_image = uploaded_file.name.lower().endswith((".png", ".jpg", ".jpeg"))
    
    if is_image:
        st.success(f"✅ Image Resume loaded: **{uploaded_file.name}**")
        st.image(uploaded_file, caption="Uploaded Resume Image", use_container_width=True)
        resume_text = ""  # Will be populated by LLM vision transcription
    else:
        resume_text = extract_text(uploaded_file)
        st.success(f"✅ Resume loaded: **{uploaded_file.name}** ({len(resume_text)} characters)")

    if st.button("Evaluate Candidate", type="primary"):
        # Step 1: LLM Screening
        with st.spinner(f"Evaluating resume for {selected_role}..."):
            if is_image:
                image_bytes = uploaded_file.getvalue()
                mime_type = "image/png" if uploaded_file.name.lower().endswith(".png") else "image/jpeg"
                result = screen_image_with_llm(image_bytes, mime_type, selected_role, role_requirements, role_skills)
                resume_text = result.get("transcription", "")
            else:
                result = screen_with_llm(resume_text, selected_role, role_requirements, role_skills)

        decision = result.get("decision", "Rejected")
        score = result.get("score", 0.0)
        justification = result.get("justification", "")

        st.divider()
        if decision == "Shortlisted":
            st.success(f"## ✅ Decision: {decision}")
        else:
            st.error(f"## ❌ Decision: {decision}")

        st.metric("Skill Match Score", f"{int(score * 100)}%")
        st.markdown(f"**Role Evaluated:** {selected_role}")
        st.markdown(f"**AI Justification:** {justification}")

        # Step 2: GovernAI Telemetry
        with st.spinner("Logging evaluation to GovernAI..."):
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
                    "privacy_filters": False
                },
                "raw_prediction": {
                    "input_text": resume_text[:2000],
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
st.caption("Monitored by GovernAI")