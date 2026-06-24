# GovernAI — Master Implementation Plan

> **Synthesized from:** project brief, technical design (`implementation_gri.md`), and architecture overview (`GovernAI_Implementation_Plan.md`)  
> **Team:** Inventory & Database Lead · Risk & Compliance Lead · Monitoring & Audit Lead  
> **Deadline:** Friday EOD

---

---

## 1. Resolved Open Questions

| Question | Decision | Rationale |
|---|---|---|
| **User identity for audit log** | Sidebar dropdown: Admin / Compliance Officer / Engineer — stored as a plain session string, no auth | Cheap to build; doubles as groundwork for the role-based-views stretch goal |
| **Metrics data source** | "Simulate Ingestion" button is the primary demo path; CSV upload is Good-to-Have if time allows Friday morning | Simulation reliably trips a threshold on command — safer for the live walkthrough |
| **Report export format** | Markdown for MVP — can be printed to PDF from the browser | Direct PDF generation is not a hard requirement and adds unnecessary complexity |
| **Storage** | SQLite (`governai.db`) — no JSON blobs; every field is a plain relational column | Allows any field to be filtered, joined, or aggregated directly in SQL |
| **Primary keys** | UUID on every table | Three people writing to the same DB independently — UUIDs avoid ID collisions across parallel work |

---

## 2. Governance Workflow

```
AI System Registration
        ↓
PII Detection  ←── Raises suggested risk tier automatically if contains_pii = true
        ↓
Risk Classification  ←── Questionnaire → stored tier
        ↓
Compliance Mapping  ←── Tier determines which EU AI Act + NIST controls are seeded
        ↓
Monitoring & Observability  ←── Threshold breach flips compliance_status
        ↓
Audit Trail  ←── Every state change appended, never overwritten
        ↓
Report Generation  ←── Pulls system details, completeness score, breach events, full audit trail
```

**The rule:** a signal in one area must change state in another. Risk tier → compliance checklist. Threshold breach → compliance status flip → visible in report. This cross-wiring is the deliverable, not the individual screens.

---

## 3. System Architecture

```
+--------------------------------------------------+
|                 Streamlit UI                     |
|  Dashboard | Inventory | Risk | Compliance |     |
|  Monitoring | Reports                            |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|            Governance Services Layer             |
|  ai_system_svc  · risk_svc  · compliance_svc    |
|  monitoring_svc · audit_svc · report_gen         |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|              Shared Governance Data (SQLite)     |
|  ai_systems · data_sources · risk_assessments    |
|  risk_classification_answers · compliance_items  |
|  monitoring_metrics · audit_logs                 |
|  agent_action_trace                              |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|          Optional AI Assistance Layer            |
|  Risk tier recommendation (stretch goal #1)      |
|  Compliance summarization · Report narratives    |
+--------------------------------------------------+
```

---

## 4. Project Structure

```
governai/
├── app.py                     # Main Streamlit entry point
├── database/
│   ├── db_manager.py          # Connection handling, table creation
│   └── seed_data.py           # 4 sample systems + metrics
├── services/
│   ├── ai_system_svc.py       # CRUD on systems + data_sources
│   ├── risk_svc.py            # Questionnaire logic, PII-aware tier suggestion
│   ├── compliance_svc.py      # Checklist generation + completeness scoring
│   ├── monitoring_svc.py      # Metric ingestion, threshold evaluation
│   └── audit_svc.py           # Append-only logging + agent_action_trace writes
├── pages/
│   ├── 1_Dashboard.py         # Portfolio health at a glance
│   ├── 2_Inventory.py         # Add / edit / view systems
│   ├── 3_Risk_Setup.py        # Guided risk classification questionnaire
│   ├── 4_Compliance.py        # Checklist, completeness score, framework mapping
│   └── 5_Monitoring.py        # Metrics dashboard, threshold controls, simulate ingestion
├── reports/
│   ├── report_gen.py          # Markdown report compiler
│   └── templates/
├── config/
│   └── settings.py            # Framework mappings, threshold defaults
└── utils/
    └── helpers.py
```

---

## 5. Data Schema

### Design principles

- UUID primary keys everywhere — collision-safe for parallel development.
- No JSON blobs — every meaningful field is its own column.
- `audit_logs` is append-only — one row per action, explicit columns for `field_changed`, `old_value`, `new_value`.
- `risk_classification_answers` stores one row per question — individual answers can be re-scored or displayed without parsing a blob.

### `ai_systems`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | text | |
| `owner` | text | |
| `business_purpose` | text | |
| `model_vendor` | text | e.g. "OpenAI GPT-4o" |
| `model_type` | enum | `llm` / `classical_ml` / `agentic` / `computer_vision` / `other` |
| `vendor_type` | enum | `proprietary_api` / `open_source_self_hosted` / `azure_ai_foundry` / `other` |
| `is_agentic` | boolean | When true, audit entries expand into step-level traces |
| `risk_tier` | enum | `prohibited` / `high` / `limited` / `minimal` |
| `compliance_status` | enum | `compliant` / `at_risk` / `non_compliant` |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### `data_sources`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `system_id` | UUID FK → ai_systems | |
| `source_name` | text | |
| `description` | text | |
| `contains_pii` | boolean | **Read directly by `risk_svc.py`** — any `true` row auto-raises the suggested tier |
| `pii_categories` | text | Comma list, e.g. "name, financial, health" — shown in compliance report as evidence |

### `risk_assessments`

One row per system per assessment. Individual Q&A lives in `risk_classification_answers`.

| Column | Type |
|---|---|
| `id` | UUID PK |
| `system_id` | UUID FK |
| `calculated_tier` | enum |
| `assessed_by` | text (session user) |
| `assessed_at` | datetime |

### `risk_classification_answers`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `system_id` | UUID FK | |
| `question_key` | text | e.g. `"uses_biometrics"` |
| `answer` | text | |
| `weight` | float | Contributes to tier scoring |

### `compliance_items`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `system_id` | UUID FK | |
| `framework` | text | `"EU AI Act"` / `"NIST AI RMF"` |
| `control_id` | text | e.g. `"Art.13"`, `"GOVERN-1.1"` |
| `description` | text | |
| `status` | enum | `complete` / `incomplete` / `not_applicable` |
| `evidence_link` | text | |
| `cross_framework_tag` | text | Marks controls satisfying more than one framework |

### `monitoring_metrics`

| Column | Type |
|---|---|
| `id` | UUID PK |
| `system_id` | UUID FK |
| `metric_name` | text |
| `value` | float |
| `threshold_warning` | float |
| `threshold_critical` | float |
| `recorded_at` | datetime |

### `audit_logs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `system_id` | UUID FK | |
| `action` | text | `SYSTEM_CREATED`, `STATUS_CHANGED`, `THRESHOLD_BREACHED`, etc. |
| `field_changed` | text | |
| `old_value` | text | |
| `new_value` | text | |
| `performed_by` | text | Session user string |
| `timestamp` | datetime | |

### `agent_action_trace`

Only populated when `is_agentic = true` on the parent system. Each row is a child of one `audit_logs` entry — a supplement, not a replacement.

| Column | Type |
|---|---|
| `id` | UUID PK |
| `audit_log_id` | UUID FK → audit_logs |
| `step_number` | integer |
| `action_taken` | text |
| `tool_used` | text |
| `decision_rationale` | text |

---

## 6. Seed Data

Four sample systems spanning different model types, vendor types, and risk tiers. Monitoring metrics are pre-seeded with one system already at a warning threshold to demonstrate the status-flip during the walkthrough.

| System | Model | Type | Vendor | Risk Tier | Key Notes |
|---|---|---|---|---|---|
| **HireIQ — Resume Screener** | OpenAI GPT-4o | LLM | Proprietary API | **High** | EU AI Act Annex III (hiring); PII: names, demographics |
| **CreditLens — Loan Scorer** | XGBoost | Classical ML | Open-source, self-hosted | **High** | Score-output, not chat; org bears full accountability; PII: financial data |
| **AskOps — Internal Chatbot** | Mistral Large via Azure AI Foundry | LLM | Azure AI Foundry | **Limited** | Managed platform with built-in content filters; no PII |
| **MeetBot — Scheduling Agent** | Llama 3.1 70B | Agentic | Open-source, self-hosted | **Limited–High (borderline)** | Multi-step agent (email → calendar → booking); each step individually traced; moderate PII |

---

## 7. Compliance Framework Coverage

### EU AI Act

| Area | Controls |
|---|---|
| Risk Categorization | Prohibited / High / Limited / Minimal tiers per Annex III |
| Transparency | Disclosures for limited-risk systems |
| Human Oversight | Override mechanisms, human-in-the-loop documentation |
| Technical Documentation | System cards, data provenance, model cards |
| Governance Reporting | Audit trail, incident records |

### NIST AI RMF

| Function | Focus |
|---|---|
| **Govern** | Policies, roles, accountability structures |
| **Map** | Context, risk identification, stakeholder impact |
| **Measure** | Metrics, monitoring, bias/drift evaluation |
| **Manage** | Response plans, threshold governance, remediation |

**Cross-framework controls** are tagged in `compliance_items.cross_framework_tag`. A single well-documented human oversight mechanism, for example, satisfies both EU AI Act Article 14 and NIST AI RMF GOVERN-1.2. The completeness score reflects this — no duplicate work.

---

## 8. Monitoring Thresholds and Governance Actions

| Condition | Compliance Status Set To |
|---|---|
| All metrics within threshold | Compliant |
| Any metric at warning threshold | At Risk |
| Any metric at critical threshold | **Non-Compliant** — also writes `audit_logs` entry and appears in report |

### Core metrics tracked

- Model drift score
- Bias / fairness indicator
- Hallucination rate
- Inference cost
- Data freshness (days since last refresh)

---

## 9. The Golden Thread (End-to-End Demo Flow)

This is the flow the Friday walkthrough follows. Every step exercises a different module; the point is that each step changes state visible in the next.

1. **System created** — "MeetBot" added with `model_type = agentic`, `vendor_type = open_source_self_hosted`. `audit_svc` writes `SYSTEM_CREATED`.
2. **Data source flagged** — calendar/contact data added with `contains_pii = true`. `risk_svc` reads this and raises the suggested tier from Limited to Limited–High.
3. **Risk classified** — tier confirmed. `compliance_svc` auto-seeds the matching EU AI Act + NIST AI RMF controls for that tier.
4. **Agent run simulated** — three steps logged (read email → checked calendar → booked meeting), each written to `agent_action_trace` under one parent `audit_logs` row.
5. **Threshold breached** — simulated cost metric exceeds critical threshold. `monitoring_svc` flips `compliance_status` to `Non-Compliant` and writes a second `audit_logs` entry.
6. **Report exported** — `report_gen` compiles system details, completeness score, the breach event, and the full audit trail including the step-by-step agent trace into one Markdown document.

---

## 10. Three-Day Timeline

### Day 1 — Wednesday: Schema and skeletons

| Who | Task |
|---|---|
| **All three** | Joint schema review and sign-off on this document (morning — nothing else starts until this is done) |
| Inventory Lead | `db_manager.py`, table creation script, `seed_data.py` with all four sample systems and pre-seeded metrics |
| Risk & Compliance Lead | `config/settings.py` (framework mappings, threshold defaults), `risk_svc.py` skeleton |
| Monitoring & Audit Lead | `monitoring_svc.py` skeleton, Simulate Ingestion button wired to threshold evaluation |

### Day 2 — Thursday: Service logic and integration wiring

| Who | Task |
|---|---|
| **All three** | Build service logic and corresponding pages against the locked schema |
| **Integration focus** | Wire `monitoring_svc` → `ai_system_svc` → `audit_svc`: breach flips status, log entry written automatically |
| **Integration focus** | Wire `risk_svc` PII-aware suggestion to `data_sources.contains_pii` |
| **Pair task** | `agent_action_trace` wiring for MeetBot — most complex cross-module path; do this together |

### Day 3 — Friday: End-to-end, report, and walkthrough

| Who | Task |
|---|---|
| Reporting Lead | `report_gen.py` — compile system details, completeness score, breach events, audit trail into Markdown |
| All | Full Golden Thread run-through end to end — verify every state change flows correctly |
| All | Rehearse live walkthrough using MeetBot as the demo system |
| All | Submit: running app + live walkthrough + one-page design-decisions writeup |

---

## 11. Stretch Goals (if Friday morning has slack)

Ordered by effort-to-demo-payoff ratio. Only attempt #2 or #3 if #1 is working.

### 1. LLM-powered risk tier assistant *(lowest cost)*

A text box where the user pastes a plain-language system description. One API call returns a suggested risk tier with a short rationale, pre-fills — but does not auto-submit — the questionnaire.
- No new tables required.
- Implementation: one `claude-sonnet` call, structured output with `tier` + `rationale` fields.

### 2. Portfolio-wide risk rollup on the landing page

`1_Dashboard.py` shows system counts by risk tier and compliance status across the whole inventory. Compliance officers get portfolio health at a glance, not just per-system detail.
- No new backend logic — just aggregation queries on existing tables.

### 3. Role-based views (Compliance Officer vs. Engineer)

Reuses the session user-identity dropdown already built for the audit log.
- Compliance Officer view: checklists, completeness scores, reports.
- Engineer view: monitoring metrics, threshold controls, raw audit log.
- Same data, filtered presentation — no new backend logic.

---

## 12. Key Design Principles

1. **Single source of truth** — every module reads from and writes to the same SQLite schema.
2. **Risk-based governance** — the risk tier is not a label; it determines which controls are required.
3. **Auditability** — the audit log is append-only; nothing is overwritten or deleted.
4. **Cross-wiring over completeness** — a working end-to-end flow takes priority over a polished individual screen.
5. **Explainability** — the questionnaire stores individual answers so any tier decision can be explained and re-scored.
6. **Human oversight** — AI assistance (stretch goal) pre-fills but never auto-submits; a human confirms every governance decision.

---

## 13. Deliverables Checklist

- [ ] Running Streamlit app seeded with four realistic sample systems
- [ ] Live walkthrough: add MeetBot (high-risk path), classify it, trip a monitoring threshold, export compliance report
- [ ] One-page design-decisions writeup covering schema choices, integration approach, and what to build next

---

*This document supersedes the three individual planning files. If a detail conflicts, this file wins. Update this file — not the originals — if decisions change during the sprint.*
