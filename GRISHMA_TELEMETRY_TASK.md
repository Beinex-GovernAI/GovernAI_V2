# GovernAI — Project Update & Task Handover

This file documents everything completed after the first Mebin demo and what still needs to be done.

---

## ✅ Work Completed (Post-Demo Session)

### 1. Expanded Regional Compliance Frameworks
**What we did:** Added native support for the **UAE Charter for AI Ethics** and **SDAIA AI Ethics Principles (Saudi Arabia)** into the core compliance engine (`compliance_svc.py`).

**Impact:** The platform is no longer limited to just the EU AI Act and NIST. System scorecards and the generated PDF Audit Reports now dynamically include compliance checklists and scores for these Middle Eastern frameworks. The `report_gen.py` PDF generator was updated to dynamically render all frameworks present for a given system, rather than hardcoding only EU AI Act and NIST.

---

### 2. Built the "Plug-and-Play" Intake API
**What we did:** Developed a brand-new, agnostic API endpoint (`POST /api/v1/scanner/intake`) in `governai/api/server.py`.

**Impact:** External AI apps can simply fire a JSON payload to this endpoint, and GovernAI will automatically:
- Register the system (if new) and assign it a risk tier via the LLM.
- Generate compliance checklists for all frameworks.
- Ingest raw prediction data for analytics.
- Apply compliance evidence from the payload.

No manual data entry from the user is required.

---

### 3. Automated Internal Telemetry & Analytics
**What we did:** Created `governai/services/analytics_svc.py`.

**Impact:** Instead of relying on external apps to compute drift and bias themselves, GovernAI now does this internally. The intake API accepts "raw predictions" (the input text, output text, and confidence score from any AI model). GovernAI then automatically calculates statistical proxies for Drift and Bias in the background and logs them to the monitoring dashboard.

---

### 4. Smart Auto-Compliance Checking
**What we did:** Added an `auto_populate_compliance()` function to `compliance_svc.py`.

**Impact:** When an AI app connects to the Intake API, it can pass evidence (e.g., a documentation URL, or a flag saying privacy filters are active). GovernAI reads this and instantly checks off the corresponding regulatory controls (like EU-ART-11 documentation controls) as "Met", significantly reducing manual compliance work.

---

### 5. Created a Real "Demo AI System" — HR Resume Screener
**What we did:** Built `resume_screener_app.py` — a fully functional standalone Streamlit web application for an HR recruiter persona.

**Impact:** This gives a realistic visual demo for Mebin. The flow is:
1. HR recruiter uploads a PDF/TXT resume.
2. The app passes text through the **Kiji Privacy Proxy** (PII masking) if it is running.
3. The (PII-safe) text is evaluated by GPT-4o-mini (or a local Foundry model) and returns a decision: *Shortlisted / Rejected* with a match score and justification.
4. In the background, the app **silently sends telemetry** to the GovernAI Intake API — no manual action required.
5. GovernAI's dashboard is updated automatically with the risk tier, drift/bias metrics, and compliance evidence.

**How to run it:**
```bash
# From the project root (g:\BEINEX.AI\GovernAI):
streamlit run resume_screener_app.py --server.port 8502
```

---

## 🔲 Work Still To Be Done

### High Priority
- [ ] **Live/Periodic Scanning** — Right now telemetry is only sent when the screener app manually fires a request. Mebin wanted *periodic automatic scanning* even when no one is actively using the demo app. A background scheduler (e.g., APScheduler) inside the screener app that pushes a telemetry heartbeat every N minutes would solve this.
- [ ] **Codebase Scanner** — Mebin mentioned "scan their codebase and verify by a verifier". This would be a module that scans an AI project's Python files (looking for model type, hyperparameters, data sources) and auto-populates the GovernAI system record without any user input.

### Medium Priority
- [ ] **Drift/Bias over Batches** — The current `analytics_svc.py` uses simple single-inference proxies. For a production-grade demo, the bias/drift calculation should accumulate across a batch of predictions and compute statistically meaningful scores.
- [ ] **Screener App Improvements** — Add job profile selection (e.g., AI Research Scientist, Frontend Dev) back to the simplified UI as a lightweight dropdown, so the demo better illustrates role-specific AI governance.

### Low Priority
- [ ] **Kiji Setup Documentation** — Document exact startup steps for the demo machine so Kiji PII masking works reliably during the Mebin demo (see `KIJI_PROXY_IMPLEMENTATION_GUIDE.md`).
- [ ] **FastAPI Server startup script** — There is no `start.sh` / `start.ps1` that launches both the Streamlit app and the FastAPI server together. A simple script would make demos smoother.

---

## 🖥️ How to Run the Full Demo

Open **3 terminals** from `g:\BEINEX.AI\GovernAI\`:

| Terminal | Command |
|---|---|
| 1. GovernAI Dashboard | `streamlit run governai/Home.py` |
| 2. FastAPI Intake API | `cd governai && uvicorn api.server:app --reload --port 8000` |
| 3. HR Resume Screener | `streamlit run resume_screener_app.py --server.port 8502` |

Then in a WSL terminal (if Kiji is set up):
```bash
cd ~/kiji-proxy && kiji-proxy
```

---

*Last updated: 2026-07-20*
