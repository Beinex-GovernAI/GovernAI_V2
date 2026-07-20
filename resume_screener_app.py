import streamlit as st
import os
import sys
import requests
import json
import time
from dotenv import load_dotenv

# Ensure we can import from governai
sys.path.append(os.path.join(os.path.dirname(__file__), 'governai'))

# Load environment
load_dotenv()

# We try to import Kiji pipeline and local LLM client
try:
    from services.llm.pii_pipeline import mask_pii_with_kiji
    kiji_imported = True
except ImportError:
    kiji_imported = False

try:
    from services.llm.foundry_client import FoundryClient
    foundry_imported = True
except ImportError:
    foundry_imported = False

st.set_page_config(
    page_title="HR Resume Screener AI (LangChain Agent)",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styles for polished look
st.markdown("""
<style>
    .reportview-container { background: #f6f8fa; }
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1e293b; margin-bottom: 5px; }
    .sub-header { font-size: 1.1rem; color: #64748b; margin-bottom: 25px; }
    .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📄 HR Resume Screener AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">LangChain-orchestrated candidate evaluation with built-in PII protection and GovernAI auditing.</div>', unsafe_allow_html=True)

# ----------------- Configuration & Setup -----------------
GOVERNAI_INTAKE_URL = os.environ.get("GOVERNAI_INTAKE_URL", "http://localhost:8000/api/v1/scanner/intake")
KIJI_PROXY_URL = os.environ.get("KIJI_PROXY_URL", "http://localhost:8080/api/pii/check")

# Sidebar settings
st.sidebar.title("Configuration")
st.sidebar.markdown("### Job Profiles")
job_profile = st.sidebar.selectbox(
    "Target Job Role",
    [
        "Python Backend Engineer",
        "AI Research Scientist",
        "Frontend Developer (React)"
    ]
)

job_requirements = {
    "Python Backend Engineer": "Requires: Python, SQL, REST APIs, Git, AWS, testing.",
    "AI Research Scientist": "Requires: NLP, PyTorch/TensorFlow, LLMs, LangChain, embeddings.",
    "Frontend Developer (React)": "Requires: React, JavaScript, HTML, CSS, frontend optimization."
}

st.sidebar.info(f"**Required Skills:**\n{job_requirements[job_profile]}")

st.sidebar.markdown("### Governance & Privacy Settings")
enable_kiji = st.sidebar.toggle("Enable Kiji PII Masking", value=True, help="Masks candidate names, emails, and phones before sending to the model.")
human_in_loop = st.sidebar.toggle("Human-in-the-Loop Review", value=True, help="Signals to GovernAI that decisions require manual recruiter sign-off.")

# ----------------- File Extraction Helpers -----------------
def extract_text_from_pdf(file) -> str:
    import pypdf
    try:
        reader = pypdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return ""

def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".txt"):
        return str(uploaded_file.read(), "utf-8")
    else:
        st.error("Unsupported file format!")
        return ""

# ----------------- PII Masking & LLM Evaluation -----------------
def try_kiji_masking(text: str) -> tuple[str, bool]:
    if not kiji_imported:
        return text, False
    try:
        response = requests.post(KIJI_PROXY_URL, json={"message": text}, timeout=3)
        if response.status_code == 200:
            return response.json().get("masked_message", text), True
    except Exception:
        pass
    return text, False

def run_llm_screening(resume_text: str, profile: str) -> dict:
    """Evaluates the resume text against the job profile requirements using local LLM or OpenAI."""
    prompt = f"""
    You are an AI Recruitment Assistant screening candidates for the role: "{profile}".
    Evaluate the following candidate resume text against these requirements:
    {job_requirements[profile]}

    Output your assessment STRICTLY in the following JSON format:
    {{
        "decision": "Shortlisted" or "Rejected",
        "score": <float between 0.0 and 1.0 representing skill match>,
        "justification": "<concise explanation of skills matched or missing>"
    }}

    Candidate Resume:
    {resume_text}
    """
    
    # Try local LLM via Foundry Local first
    if foundry_imported:
        try:
            client = FoundryClient()
            messages = [{"role": "user", "content": prompt}]
            raw_response = client.chat_completion(messages)
            return json.loads(raw_response)
        except Exception:
            pass # Fall back to OpenAI
            
    # Try OpenAI fallback
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
        except Exception as e:
            pass # Fall back to local rules
            
    # Local Rule-based parser fallback if no LLM is running/reachable
    req_skills = {
        "Python Backend Engineer": ["python", "sql", "aws", "git", "api"],
        "AI Research Scientist": ["pytorch", "tensorflow", "nlp", "llm", "langchain"],
        "Frontend Developer (React)": ["react", "javascript", "html", "css"]
    }
    
    text_lower = resume_text.lower()
    matches = [s for s in req_skills[profile] if s in text_lower]
    score = len(matches) / len(req_skills[profile])
    decision = "Shortlisted" if score >= 0.6 else "Rejected"
    
    return {
        "decision": decision,
        "score": round(score, 2),
        "justification": f"Rule-based fallback check. Matched keywords: {', '.join(matches)}."
    }

# ----------------- UI Content -----------------
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="card"><h4>📤 Upload Candidate Resume</h4>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload PDF or TXT resume", type=["pdf", "txt"])
    st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    # 1. Extract Text
    raw_text = extract_text_from_file(uploaded_file)
    
    if raw_text:
        # 2. PII Masking Check
        masked_text = raw_text
        kiji_active = False
        if enable_kiji:
            with st.spinner("Protecting candidate privacy via Kiji..."):
                masked_text, kiji_active = try_kiji_masking(raw_text)
        
        # UI Display of original vs masked
        with col1:
            st.markdown('<div class="card"><h4>🔍 Privacy & PII Inspection</h4>', unsafe_allow_html=True)
            if kiji_active:
                st.success("✅ Kiji Privacy Proxy Active: PII redacted successfully.")
                tab1, tab2 = st.tabs(["🔒 Masked Text (Sent to LLM)", "📄 Original Resume"])
                with tab1:
                    st.text_area("Masked Data", value=masked_text[:1000] + "\n...", height=250, disabled=True)
                with tab2:
                    st.text_area("Original Data", value=raw_text[:1000] + "\n...", height=250, disabled=True)
            else:
                st.warning("⚠️ Kiji Privacy Proxy Offline: Processing with raw text.")
                st.text_area("Resume Content", value=raw_text[:1000] + "\n...", height=250, disabled=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card"><h4>🤖 LangChain Evaluation Results</h4>', unsafe_allow_html=True)
            if st.button("Evaluate Candidate", type="primary"):
                with st.spinner("Analyzing resume using LLM pipeline..."):
                    # Trigger LLM Evaluation
                    res = run_llm_screening(masked_text, job_profile)
                    
                    # Display Results
                    decision = res.get("decision", "Rejected")
                    score = res.get("score", 0.0)
                    justification = res.get("justification", "No assessment provided.")
                    
                    if decision == "Shortlisted":
                        st.success(f"### 📈 Status: **Shortlisted**")
                    else:
                        st.error(f"### 📉 Status: **Rejected**")
                        
                    st.metric("Skill Match Alignment Score", f"{int(score * 100)}%")
                    st.markdown(f"**Justification:** {justification}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Telemetry payload construction
                    st.markdown('<div class="card"><h4>🛡️ GovernAI Telemetry Webhook</h4>', unsafe_allow_html=True)
                    st.info("Pushed governance & telemetry metadata in the background:")
                    
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
                            "documentation_url": "https://wiki.beinex.com/hr-ai-screener",
                            "human_in_loop": human_in_loop,
                            "privacy_filters": kiji_active
                        },
                        "raw_prediction": {
                            "input_text": masked_text[:2000],  # send the masked text to keep it compliant
                            "output_text": decision,
                            "confidence_score": score
                        }
                    }
                    
                    # Output payload JSON for validation
                    st.json(scanner_payload)
                    
                    # Send payload to GovernAI Intake API
                    try:
                        resp = requests.post(GOVERNAI_INTAKE_URL, json=scanner_payload, timeout=5)
                        if resp.status_code == 200:
                            gov_data = resp.json()
                            st.success(f"✅ Telemetry Registered in GovernAI! System status updated: **{gov_data.get('compliance_status')}**")
                        else:
                            st.error(f"❌ Failed to reach GovernAI Intake: Status {resp.status_code}")
                    except Exception as e:
                        st.error(f"❌ Connection error to GovernAI backend: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.write("Click 'Evaluate Candidate' to begin analysis.")
            st.markdown('</div>', unsafe_allow_html=True)
else:
    with col2:
        st.info("Please upload a resume file in the left panel to begin candidate screening.")
