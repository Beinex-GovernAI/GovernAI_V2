# GovernAI — Complete Progress Summary

Consolidated from three workstreams: the original post-demo handover, Grishma's task-completion summary, and this session's codebase scanner build + batch drift/bias testing. Reflects what's actually done, tested, and verified — not just written.

---

## ✅ Foundational Work (Post-First-Demo)

### 1. Expanded Regional Compliance Frameworks
Added native support for the **UAE Charter for AI Ethics** and **SDAIA AI Ethics Principles (Saudi Arabia)** into `compliance_svc.py`, alongside EU AI Act and NIST. `report_gen.py` dynamically renders whichever frameworks apply to a given system in the generated PDF Audit Report.

### 2. Plug-and-Play Intake API
Built `POST /api/v1/scanner/intake` in `governai/api/server.py`. External AI apps fire a single JSON payload and GovernAI automatically registers the system, assigns a risk tier via LLM, generates compliance checklists, ingests raw prediction data, and applies compliance evidence — no manual entry required.

### 3. Automated Internal Telemetry & Analytics
Created `governai/services/analytics_svc.py` so GovernAI computes drift/bias internally from raw prediction data submitted via the intake API, rather than relying on external apps to compute it themselves.

### 4. Smart Auto-Compliance Checking
Added `auto_populate_compliance()` to `compliance_svc.py`. Evidence passed via the Intake API (e.g. a documentation URL, or a flag that privacy filters are active) automatically checks off the corresponding regulatory controls as "Met."

### 5. Demo AI System — HR Resume Screener
Built `resume_screener_app.py`: uploads a resume → passes through **Kiji Privacy Proxy** for PII masking → evaluated by GPT-4o-mini (or local Foundry model) → Shortlisted/Rejected decision → silently sends telemetry to GovernAI in the background.

---

## ✅ Live/Periodic Scanning (Heartbeat)

**Problem:** Telemetry only fired when the screener was actively used — no way to show a system as "continuously monitored" in between.

**Built:**
- `POST /api/v1/systems/{system_id}/heartbeat` — updates only `AISystem.updated_at`. Deliberately does **not** trigger compliance re-checks, log fake Drift/Bias metrics, or write audit log entries, so pings can't be mistaken for real prediction events.
- `resume_screener_app.py` registers itself once on startup via `/scanner/intake` (metadata only, no `raw_prediction` — avoids logging fake analytics at registration).
- Background `APScheduler` job pings `/heartbeat` every N minutes (`GOVERNAI_HEARTBEAT_MINUTES` env var, default 5), independent of user activity.
- Uses `@st.cache_resource` so the scheduler starts once per server process despite Streamlit re-running the script on every interaction.

**Verified:** Direct DB check before/after a manual `/heartbeat` call confirmed only `updated_at` changes. Left the app open with a 1-minute test interval and no interaction — confirmed `updated_at` advanced on its own.

---

## ✅ Batch-Based Drift/Bias

**Problem:** Original `calculate_drift()`/`calculate_bias()` scored each prediction in isolation (confidence level, input length, keyword matches) — not statistically meaningful. Real drift/bias detection needs a batch of predictions compared against each other or a baseline.

### Approach
Every prediction hitting the intake API is now persisted. Drift/bias is computed over the last N (30) predictions per system, not one inference at a time.

### Database (Supabase Postgres)
New `raw_predictions` table (system_id FK, input_text, output_text, confidence_score, sensitive_flag, created_at), with a composite index on `(system_id, created_at DESC)`. Run without Row Level Security — all DB access goes through the FastAPI backend, not client-side Supabase calls. Matching `RawPrediction` SQLAlchemy model added, with a relationship on `AISystem`.

### Batch Drift — Population Stability Index (PSI)
`calculate_batch_drift()` splits a system's last N predictions into an older half (reference) and newer half (current), measuring how much the confidence-score distribution shifted between them via PSI. Falls back to input-length distribution if confidence scores aren't populated. Needs ≥6 stored predictions before returning a non-zero score.

### Batch Bias — Confidence Gap by Keyword Proxy
`calculate_batch_bias()` compares average confidence between predictions whose input mentioned a sensitive keyword (gender, race, age, religion, etc.) vs. those that didn't — a proxy, not a true protected-class fairness metric, since the payload schema has no demographic field to group on. Falls back to keyword-density scoring until both flagged and unflagged predictions exist.

### Pruning
Rows beyond the most recent 30 per system are deleted on every new insert — no separate cron job needed.

### Testing & Debugging
A synthetic test harness (`test_batch_drift_bias.py`) fired two phases of predictions straight at the intake API: a baseline batch (confidence tightly clustered ~0.85) and a drifted batch (lower, wider spread) — designed to validate that PSI reacts to distribution *shape* change, not just average.

This testing surfaced and fixed three real bugs in `server.py`:
1. **Stale function calls** — `scanner_intake()` was still calling the old `calculate_drift()`/`calculate_bias()` instead of the renamed batch versions, causing a `NameError` 500.
2. **Indentation slip** — `save_raw_prediction(...)` and following lines lost indentation under the `if payload.raw_prediction:` block after the fix above, causing an `IndentationError` on startup.
3. **Wrong import path** — a stray `from governai.database import db` line (likely an editor autocomplete artifact) alongside the correct `from database.db import get_db`, silently breaking the server on every reload and surfacing client-side as confusing read-timeouts.

**Result — confirmed working end-to-end:** the drifted batch produced a PSI of 0.462 against a 0.15 threshold, which correctly flipped a system's compliance status from "At Risk" to "Non-Compliant" with a full audit log entry — the complete chain (synthetic batch → PSI calculation → threshold breach → compliance status flip → audit log) verified working.

---

## ✅ Codebase Scanner (`codebase_scanner.py`)

**Mebin's ask:** "scan their codebase and verify by a verifier" — a module that scans an AI project's Python files (model type, hyperparameters, data sources) and auto-populates the GovernAI system record without manual input.

### How it works
Uses Python's `ast` module (not regex) to statically walk a target project's `.py` files and detect:

| Category | What it looks for | Example |
|---|---|---|
| Framework | Import statements + model constructor calls | `OpenAI`, `sklearn`, `torch` |
| Hyperparameter | Kwargs passed to model constructors | `n_estimators=100`, `temperature=0.7` |
| Data source | Calls like `read_csv`, `open`, `create_engine` | CSV files, DB connections |
| Sensitive data | Keyword matches in identifiers/strings | `email`, `ssn`, `resume`, `candidate` |
| Evidence hint: privacy_filters | Imports/calls like `kiji`, `mask_pii`, `anonymize` | Real Kiji Privacy Proxy usage |
| Evidence hint: human_in_loop | Calls like `approve`, `human_review` | — |

### The "verifier" requirement
Nothing is auto-confirmed. Every detection is tagged `status: "detected_unverified"`. The two evidence hints only get sent as `True` to the compliance system if explicitly confirmed via `--confirm-privacy-filters` / `--confirm-human-in-loop` flags after manual review — matching Mebin's "scan + verify" ask rather than blind auto-trust.

### Integration
POSTs directly to the existing `POST /api/v1/scanner/intake` endpoint (same one `resume_screener_app.py` uses) rather than a new ingestion path. Payload validated against the real `ScannerPayload` schema and `auto_populate_compliance()`'s expected evidence dict shape (`documentation_url`, `human_in_loop`, `privacy_filters`).

### Usage
```bash
# Dry run — just see what it finds
python codebase_scanner.py /path/to/project \
    --system-name "HR Resume Screener" \
    --owner "Grishma" \
    --business-purpose "Screens resumes for HR shortlisting" \
    --dry-run

# After reviewing hints, confirm and send
python codebase_scanner.py /path/to/project \
    --system-name "HR Resume Screener" \
    --owner "Grishma" \
    --business-purpose "Screens resumes for HR shortlisting" \
    --confirm-privacy-filters \
    --documentation-url "https://..."
```
Outputs `scan_report_full_<name>.json` (full detail, for audit) and `scan_payload_<name>.json` (exactly what got POSTed).

**Verified — live test result:** run against the real project, correctly detected OpenAI usage, 3 real Kiji privacy-filter hints, and 21 sensitive-data keyword matches. After confirming with `--confirm-privacy-filters`, the dashboard audit trail showed control `SDAIA-2.1` (Privacy & Security) flip to `is_met: true`, evidence-linked to `"Auto-detected: privacy_filters=True"`, attributed to `scanner_integration`.

---

## ✅ Screener App Improvements (Job Profile Dropdown)

**Problem:** Screener was hardcoded to evaluate every resume against a single "Python Backend Engineer" profile.

**Built:** `JOB_PROFILES` dict with 4 roles (Python Backend Engineer, AI Research Scientist, Frontend Developer, Data Analyst), each with its own requirements string and keyword skill list. `st.selectbox` dropdown added to the UI; selection drives both the LLM prompt and keyword-matching fallback. GovernAI's `business_purpose` field now reflects the selected role.

---

## ✅ Kiji Setup Documentation

**Built:** `KIJI_QUICKSTART.md` — short, action-oriented doc covering one-time setup, daily start command, what a healthy startup log looks like, a benign warning to ignore (system proxy on WSL), a `curl` sanity check to confirm PII masking is live, and a troubleshooting table. Existing `KIJI_PROXY_IMPLEMENTATION_GUIDE.md` kept for deeper root-cause explanations.

---

## ✅ FastAPI + Streamlit Startup Scripts

**Built:** `start.ps1` / `stop.ps1` (PowerShell) — launches FastAPI Intake API, GovernAI Dashboard, and HR Resume Screener together, each logging to its own file under `logs/`. Kiji intentionally excluded (only runs cleanly from WSL) — a reminder line prints instructing the user to start it separately. An initial WSL-native `start.sh`/`stop.sh` pair was also built, but the split environment (Kiji in WSL, app stack in Windows Python) meant the PowerShell scripts are the ones actually in use.

**Verified:** Ran `.\start.ps1`, confirmed all 3 services bind to their ports with no errors in `_err.log` files, and confirmed Dashboard/Screener rendered in-browser.

---

## How to Run the Full Demo

```
.\start.ps1
```
launches FastAPI Intake API, GovernAI Dashboard, and HR Resume Screener together.

In a WSL terminal (Kiji must be started separately):
```bash
cd ~/kiji-proxy && kiji-proxy
```

---

*Last updated: 2026-07-21*
