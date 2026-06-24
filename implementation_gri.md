# GovernAI — Technical Design & Implementation Plan

**Team:** Grishma George (Inventory & Database Lead) · Member 2 (Risk & Compliance Lead) · Member 3 (Monitoring & Audit Lead)
**Timeline:** 3-day sprint, deliverable due Friday EOD

---

## 1. Decisions on Open Questions

| Question | Decision |
|---|---|
| **User identity for audit log** | Simple sidebar dropdown (Admin / Compliance Officer / Engineer), stored as a plain string per session — not authenticated. Cheap to build and doubles as groundwork for the role-based-views stretch goal. |
| **Metrics data source** | "Simulate Ingestion" button is the primary path for the demo, since it reliably trips a threshold on command. CSV upload is built as Good-to-Have if time allows Friday morning. |
| **Report export format** | Markdown export for the MVP — renders cleanly and can be printed to PDF from the browser if needed. Direct PDF generation is not a hard requirement. |

---

## 2. Schema

All tables use UUID primary keys rather than autoincrement, since three people are writing to the same SQLite database independently and UUIDs avoid ID collisions across parallel work. Every field is a plain relational column — no JSON blobs — so any field can be filtered, joined, or aggregated directly in SQL.

### 2.1 Common patterns

- **UUID primary keys** on every table.
- **`audit_logs`** records one action per row with explicit columns (`action`, `field_changed`, `old_value`, `new_value`) rather than a combined detail blob.
- **`risk_classification_answers`** stores one row per questionnaire question (`question_key`, `answer`, `weight`) rather than a combined answers blob, so individual answers can be queried or re-scored later.

### 2.2 `ai_systems`

Each system record carries structured fields describing what kind of model it is and who's accountable for it, so the inventory can actually distinguish system types rather than storing that as a free-text note:

- `model_type` — enum: `llm` / `classical_ml` / `agentic` / `computer_vision` / `other`
- `vendor_type` — enum: `proprietary_api` / `open_source_self_hosted` / `azure_ai_foundry` / `other`
- `is_agentic` — boolean; determines whether a system's audit entries expand into step-level traces (see 2.4)

Data sources are not stored as a field on this table — they live in their own table (2.3), since a flat string can't carry a PII flag or be queried by the risk engine.

### 2.3 `data_sources`

| Field | Purpose |
|---|---|
| `id` (UUID), `system_id` (FK) | Standard keys |
| `source_name`, `description` | What the data is and where it comes from |
| `contains_pii` (boolean) | Read directly by `risk_svc.py` — if any linked source is `true`, the questionnaire auto-raises the suggested risk tier |
| `pii_categories` (text) | Comma list, e.g. "name, financial, health" — shown in the compliance report as evidence |

### 2.4 `agent_action_trace`

Ensures an agentic system's actions are individually traceable, rather than its audit entry reading only "status changed."

- Linked via `audit_log_id` — each row is a child of one `audit_logs` entry, not a replacement for it.
- `step_number`, `action_taken`, `tool_used`, `decision_rationale` — one row per discrete step (e.g. step 1: read email; step 2: checked calendar; step 3: booked meeting).
- Only populated when `is_agentic = true` on the parent system.

### 2.5 `risk_assessments` and `risk_classification_answers`

`risk_assessments` stores one row per system per assessment (`system_id`, `calculated_tier`, `assessed_by`, `assessed_at`). The individual questions and answers behind that tier live in a separate `risk_classification_answers` table (`system_id`, `question_key`, `answer`, `weight`), so the questionnaire logic can read, re-score, or display individual answers without parsing a blob.

---

## 3. Application Structure

```
governai/
├── app.py                 # Main Streamlit entry point
├── database/
│   ├── db_manager.py      # Connection handling, table creation
│   └── seed_data.py       # 4 sample systems
├── services/
│   ├── ai_system_svc.py   # CRUD on systems + data_sources
│   ├── compliance_svc.py  # Checklist generation + scoring
│   ├── monitoring_svc.py  # Metric ingestion, threshold checks
│   ├── risk_svc.py        # Questionnaire logic, PII-aware tier suggestion
│   └── audit_svc.py       # Append-only logging + agent_action_trace writes
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Inventory.py
│   ├── 3_Risk_Setup.py
│   ├── 4_Compliance.py
│   └── 5_Monitoring.py
├── reports/
│   ├── report_gen.py      # Markdown report compiler
│   └── templates/
├── config/
│   └── settings.py        # Framework mappings, threshold defaults
└── utils/
    └── helpers.py
```

---

## 4. Seed Data — Sample Systems

The app is seeded with four sample systems spanning different model types, vendor types, and risk tiers, including a hiring screener as high-risk and an internal chatbot as limited-risk:

| System | Model | Type | Risk Tier | Notes |
|---|---|---|---|---|
| **Resume Screener** | OpenAI GPT-4o | LLM, proprietary API | High | EU AI Act Annex III hiring category; PII present (names, demographics) |
| **Credit Risk Scorer** | XGBoost | Classical ML, open-source, self-hosted | High | Non-chat, score-output model; org bears full accountability since self-hosted; PII present (financial data) |
| **Internal HR Chatbot** | Mistral Large via Azure AI Foundry | LLM, managed platform | Limited | Demonstrates a managed platform with built-in content filters/model cards; no PII |
| **Meeting Scheduling Agent** | Llama 3.1 70B, open-source, self-hosted | Agentic | Limited–High (borderline) | Multi-step agent (reads email → checks calendar → books meeting); each step individually logged; moderate PII (contacts, calendar data) |

Both example types named in the project scope are covered directly (Resume Screener = hiring screener / high-risk, HR Chatbot = chatbot / limited-risk), with two additional systems added for model-type and vendor-type variety.

---

## 5. The Golden Thread (End-to-End Data Flow)

1. **System created:** "Meeting Scheduling Agent" added with `model_type = agentic`, `vendor_type = open_source_self_hosted`. `audit_svc` logs `SYSTEM_CREATED`.
2. **Data source flagged:** calendar/contact data source added with `contains_pii = true`. `risk_svc` reads this and raises the suggested tier.
3. **Risk classified:** tier confirmed as Limited–High. `compliance_svc` auto-seeds the matching EU AI Act / NIST controls.
4. **Agent runs (simulated):** three steps logged — read email, checked calendar, booked meeting — each written to `agent_action_trace` under one parent `audit_logs` row.
5. **Metric breach:** simulated cost metric exceeds threshold. `monitoring_svc` flips `compliance_status` to Non-Compliant and writes a second `audit_logs` entry.
6. **Report exported:** `report_gen` compiles system details, the completeness score, the breach, and the full audit trail — including the step-by-step agent trace — into one document.

---

## 6. Revised 3-Day Timeline

### Day 1 (Wednesday)
-  joint schema review and sign-off on this design (open questions settled, schema changes in §2 confirmed).
- Inventory Lead: `db_manager.py`, table creation, `seed_data.py` with the four sample systems.
- Risk & Compliance Lead: framework mappings in `config/settings.py`, `risk_svc.py` skeleton.
- Monitoring Lead: `monitoring_svc.py` skeleton, Simulate Ingestion button.

### Day 2 (Thursday)
- All three: build out service logic and corresponding pages against the locked schema.
- Integration: wire `monitoring_svc` → `ai_system_svc` → `audit_svc` so a breach flips status and logs automatically; wire `risk_svc`'s PII-aware suggestion to `data_sources`.
- Pair on `agent_action_trace` wiring for the Meeting Scheduling Agent — the most complex cross-module path.

### Day 3 (Friday)
- Morning: `report_gen.py`, full Golden Thread run-through end to end.
- Midday: rehearse the live walkthrough using the Meeting Scheduling Agent as the demo system.
- Submit: working app, live walkthrough, one-page design-decisions writeup.

---

## 7. Stretch Goals (if finished early)

Agreed stretch directions, in priority order:

1. **LLM-powered risk tier assistant** — a text box where a user pastes a plain-language description of a system (e.g. "an internal tool that screens job applicants using resume text"), and an LLM call suggests a risk tier with a short rationale, pre-filling — but not auto-submitting — the questionnaire. Lowest implementation cost: one API call, no new tables needed.
2. **Portfolio-wide risk rollup on the landing page** — a summary view on `1_Dashboard.py` showing system counts by risk tier and by compliance status across the whole inventory, so the dashboard reflects portfolio health at a glance rather than only per-system detail.
3. **Role-based views (Compliance Officer vs. Engineer)** — reuses the session user-identity dropdown already built for the audit log (§1): a Compliance Officer view surfaces checklists and reports; an Engineer view surfaces monitoring metrics and thresholds. Same data, filtered presentation — no new backend logic required.

These are ordered by effort vs. visible payoff for a live walkthrough; only attempt #2 or #3 if #1 is already working.