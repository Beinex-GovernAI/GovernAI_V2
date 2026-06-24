# GovernAI Technical Design Document & Implementation Plan

## Goal Description
The objective is to build "GovernAI", a Streamlit-based AI Governance Platform MVP by Friday EOD. This internal tool will help organizations track their AI systems, classify their risk according to the EU AI Act, map compliance against frameworks (EU AI Act, NIST AI RMF), monitor operational metrics (drift, bias, hallucination rate, cost), and provide audit-ready reporting. The core value proposition is the seamless integration between these modules: a system's risk tier dictates its compliance checklist, and breached monitoring metrics automatically degrade compliance status and trigger audit logs.

## Key Design Decisions

> [!NOTE]
> 1. **User Identity:** Implement a lightweight session-based role selector (Admin, Compliance Officer, Engineer) in the sidebar for the MVP. This improves audit trail realism and user context during the demo while avoiding the complexity of full authentication.
> 2. **Metrics Data Source:** Prioritize a simulation-based ingestion workflow (e.g., "Generate Breach Scenario" button) to reliably and instantly demonstrate threshold breaches, automated compliance status degradation, and audit logging during the walkthrough. CSV upload will be treated as a secondary, stretch feature.
> 3. **Report Format:** Generate reports directly as PDF documents (using ReportLab). Governance and compliance workflows typically require auditor-ready, formatted artifacts, making PDF the preferred export format for the MVP.

---

## STEP 1: Requirement Analysis

**Business Objective:**
To provide organizations with a centralized internal tool to inventory their AI systems, assess their risk levels, manage framework-specific compliance, and monitor operational safety. This tool acts as the single source of truth for AI governance, specifically targeting the upcoming EU AI Act enforcement deadlines.

**Functional Requirements:**
1. **AI Inventory:** Create, Read, Update, Delete (CRUD) AI systems (name, owner, purpose, model, data sources).
2. **Risk Classification:** Guided questionnaire to assign an EU AI Act risk tier (Prohibited, High-risk, Limited-risk, Minimal-risk).
3. **Compliance Mapping:** Generate compliance checklists based on risk tier covering EU AI Act and NIST frameworks. Calculate a completeness score. Show how single controls map to multiple frameworks.
4. **Monitoring & Alerts:** Ingest operational metrics (drift, bias, hallucination, cost) via CSV or simulation. Set and monitor thresholds.
5. **State Integration:** Automatically update compliance status to "Non-Compliant" or "At Risk" when thresholds are breached.
6. **Audit Trail:** Append-only logging of all state changes (status updates, threshold breaches, edits).
7. **Reporting:** Export audit-ready compliance reports for individual systems.

**Non-Functional Requirements:**
1. **Tech Stack:** Streamlit (Frontend), SQLite (Database), Python (Backend).
2. **Data Integrity:** Shared, normalized data model acting as the single source of truth.
3. **Delivery:** Functional end-to-end flow over disconnected polished screens. Seeded with realistic sample data.

**Assumptions & Ambiguities:**
- *Assumption:* A single SQLite database file is sufficient for concurrent reads/writes given the expected MVP usage.
- *Assumption:* "Compliance Status" is a derived state (e.g., Compliant, Non-Compliant, At Risk) influenced by both manual checklist completion and automated monitoring metrics.
- *Ambiguity:* The exact questions for the risk questionnaire are not strictly defined; we will use standard representative EU AI Act criteria.

---

## STEP 2: Architecture Design

**Production-Style MVP Architecture**

```text
+-----------------------------------------------------------------------------+
|                              STREAMLIT FRONTEND                             |
|  +--------------+  +---------------+  +--------------+  +----------------+  |
|  | System Vault |  | Risk Assessor |  | Monitor Dash |  | Report Builder |  |
|  +--------------+  +---------------+  +--------------+  +----------------+  |
+---------+------------------+-------------------+------------------+---------+
          |                  |                   |                  |
+---------v------------------v-------------------v------------------v---------+
|                               PYTHON BACKEND                                |
|  +----------------+  +-------------------+  +----------------------------+  |
|  | CRUD Services  |  | Risk Engine       |  | Compliance Mapping Engine  |  |
|  +----------------+  +-------------------+  +----------------------------+  |
|  +----------------+  +-------------------+  +----------------------------+  |
|  | Reporting Layer|  | Monitoring Engine |  | Audit Logging Layer        |  |
|  +----------------+  +-------------------+  +----------------------------+  |
+------------------------------------+----------------------------------------+
                                     |
+------------------------------------v----------------------------------------+
|                            SQLITE DATABASE (ORM/SQL)                        |
|  [AI Systems] [Risk Assessments] [Compliance Records] [Metrics] [Audit Logs]|
+-----------------------------------------------------------------------------+
```

**Component Interaction & Data Flow:**
1. **User -> Frontend:** User interacts with Streamlit pages.
2. **Frontend -> Backend Services:** Streamlit calls modular Python functions (e.g., `update_system_status()`, `ingest_metrics()`).
3. **Backend -> Database:** Services execute SQLite transactions. 
4. **Cross-Component Flow:** If the `Monitoring Engine` detects a metric breach, it emits an event/calls a function in the `CRUD Services` to update the AI System's status, which in turn calls the `Audit Logging Layer` to record the change.

---

## STEP 3: Database Design

We will use a normalized SQLite schema managed via Python's standard `sqlite3` library for simplicity in the MVP.

**1. AI Systems (`ai_systems`)**
- `id` (TEXT) - Primary Key (UUID)
- `name` (TEXT)
- `owner` (TEXT)
- `business_purpose` (TEXT)
- `model_vendor` (TEXT)
- `model_type` (TEXT) - (LLM, Classical ML, Computer Vision, Agentic AI)
- `model_source` (TEXT) - (Open Source, Proprietary)
- `contains_pii` (TEXT) - (Yes, No)
- `agentic_trace_required` (TEXT) - (Yes, No)
- `data_sources` (TEXT)
- `risk_tier` (TEXT) - (Prohibited, High, Limited, Minimal, Pending)
- `compliance_status` (TEXT) - (Compliant, At Risk, Non-Compliant, Pending)
- `created_at` (TEXT) - ISO8601 Timestamp
- `updated_at` (TEXT) - ISO8601 Timestamp

**2. Risk Assessments (`risk_assessments`)**
- `id` (TEXT) - Primary Key (UUID)
- `system_id` (TEXT) - Foreign Key -> `ai_systems.id`
- `question_responses` (TEXT) - JSON string of the questionnaire answers
- `calculated_tier` (TEXT)
- `assessed_by` (TEXT)
- `assessed_at` (TEXT) - ISO8601 Timestamp

**3. Compliance Records (`compliance_records`)**
- `id` (TEXT) - Primary Key (UUID)
- `system_id` (TEXT) - Foreign Key -> `ai_systems.id`
- `framework` (TEXT) - (e.g., EU AI Act, NIST)
- `control_id` (TEXT) - Identifier for the specific requirement
- `control_description` (TEXT)
- `is_met` (INTEGER) - 0 or 1
- `evidence_link` (TEXT)
- `last_updated` (TEXT) - ISO8601 Timestamp

**4. Monitoring Metrics (`monitoring_metrics`)**
- `id` (TEXT) - Primary Key (UUID)
- `system_id` (TEXT) - Foreign Key -> `ai_systems.id`
- `metric_name` (TEXT) - (e.g., Drift, Bias, Hallucination, Cost)
- `metric_value` (REAL)
- `threshold_value` (REAL)
- `is_breached` (INTEGER) - 0 or 1
- `timestamp` (TEXT) - ISO8601 Timestamp

**5. Audit Logs (`audit_logs`)**
- `id` (TEXT) - Primary Key (UUID)
- `system_id` (TEXT) - Foreign Key -> `ai_systems.id`
- `user` (TEXT) - Who made the change
- `action` (TEXT) - (e.g., STATUS_CHANGE, METRIC_BREACH, SYSTEM_CREATED)
- `details` (TEXT) - JSON string containing old_value, new_value, or breach context
- `timestamp` (TEXT) - ISO8601 Timestamp

---

## STEP 4: Application Structure

```text
governai/
├── app.py                 # Main Streamlit entry point (Navigation, layout)
├── database/
│   ├── db_manager.py      # SQLite connection pooling, table creation scripts
│   └── seed_data.py       # Script to populate the 3-4 realistic sample systems
├── services/
│   ├── ai_system_svc.py   # Logic for CRUD operations on systems
│   ├── compliance_svc.py  # Logic for generating checklists and scoring
│   ├── monitoring_svc.py  # Logic for metric ingestion, threshold checks
│   ├── risk_svc.py        # Questionnaire evaluation logic
│   └── audit_svc.py       # Append-only logging logic
├── pages/
│   ├── 1_Dashboard.py     # High-level portfolio view
│   ├── 2_Inventory.py     # Add/Edit systems
│   ├── 3_Risk_Setup.py    # Questionnaire UI
│   ├── 4_Compliance.py    # Checklist and mapping UI
│   └── 5_Monitoring.py    # Metric charts and ingestion UI
├── reports/
│   ├── report_gen.py      # Logic for compiling Markdown/PDF reports
│   └── templates/         # Markdown templates for reports
├── config/
│   └── settings.py        # Global constants, threshold defaults, framework mappings
├── utils/
│   └── helpers.py         # UI helper functions, date formatters
└── assets/                # Logos, custom CSS (if any)
```

---

## STEP 5: Module Breakdown

**Module 1: AI System Inventory**
- **Responsibilities:** Central registry management.
- **UI Components:** Data table of all systems, forms for creating/editing, detailed view modal/page.
- **Backend Logic:** `ai_system_svc.py` handles input validation and DB insertion.
- **Database Interactions:** Reads/writes to `ai_systems`.

**Module 2: Risk Classification & Compliance**
- **Responsibilities:** Assess risk and map framework controls.
- **UI Components:** Step-by-step wizard for questionnaire. Checklist UI with checkboxes and evidence link text inputs. Progress bar for completeness score.
- **Backend Logic:** `risk_svc.py` evaluates answers to assign tiers. `compliance_svc.py` fetches the right controls based on tier and framework, calculates percentage of `is_met == True`. Shows cross-mapping (e.g., Control A satisfies both EU AI Act Art. 10 and NIST MAP 1.1).
- **Database Interactions:** Writes to `risk_assessments`, generates and updates rows in `compliance_records`.

**Module 3: Monitoring & Audit**
- **Responsibilities:** Track performance and maintain immutable history.
- **UI Components:** Line charts for drift/bias over time. CSV uploader / Simulate button. Audit log timeline view.
- **Backend Logic:** `monitoring_svc.py` compares new metric values against predefined thresholds. If breached, calls `ai_system_svc.py` to change status, which calls `audit_svc.py`.
- **Database Interactions:** Inserts into `monitoring_metrics`, updates `ai_systems.compliance_status`, inserts into `audit_logs`.

**Module 4: Reporting**
- **Responsibilities:** Generate auditor-ready artifacts.
- **UI Components:** "Export Report" button on the system detail view.
- **Backend Logic:** `report_gen.py` queries all tables for a specific `system_id`, formats them into a structured Markdown string, and provides it as a downloadable file.
- **Database Interactions:** Read-only queries across all tables.

---

## STEP 6: Integration Logic

**The Golden Thread (Data Lifecycle Flow):**
The true value of GovernAI is that data does not sit in silos. Here is how data flows through the application:

1. **System Created:** User creates "HR Resume Screener" -> DB creates `ai_systems` record. `audit_svc` logs `SYSTEM_CREATED`.
2. **Risk Classified:** User answers risk questionnaire -> `risk_svc` assigns "High-Risk" tier. Updates `ai_systems.risk_tier`. `audit_svc` logs `TIER_ASSIGNED`.
3. **Controls Generated:** `compliance_svc` detects "High-Risk" and automatically seeds `compliance_records` with EU AI Act High-Risk obligations (e.g., Data Governance, Human Oversight) and maps them to NIST.
4. **Metrics Ingested:** User uploads a CSV or simulates metrics. `monitoring_svc` processes a Bias indicator of 0.85 (predefined threshold is 0.80).
5. **The Cross-Wiring Trigger:** `monitoring_svc` detects the breach. It executes an atomic backend flow:
   - Saves the metric in `monitoring_metrics` with `is_breached = True`.
   - Calls `ai_system_svc.update_status(system_id, "Non-Compliant")`.
   - Calls `audit_svc.log_action("METRIC_BREACH", "Bias exceeded 0.80. Status changed to Non-Compliant")`.
6. **Report Exported:** User clicks "Export Report". `report_gen` compiles the system details, the compliance completeness score, the active breached metric alert, and the audit trail into a single document, proving end-to-end governance.

---

## STEP 7: Team Distribution (Assuming 3 Developers)

*Total Duration: Wednesday - Friday (3-Day Compressed Timeline).*

- **Developer 1 (Data & Core Backend):**
  - Setup SQLite database schema and connection (`db_manager.py`).
  - Create the `seed_data.py` script with the following realistic sample systems:
    - **Resume Screening AI** (High Risk, LLM)
    - **Loan Approval AI** (High Risk, Classical ML)
    - **Customer Support Assistant** (Limited Risk, LLM)
    - **Meeting Scheduling Agent** (Moderate Risk / Agentic AI)
  - Build `ai_system_svc.py` and `audit_svc.py`.
  - Build the main `app.py` scaffolding and Inventory UI (`2_Inventory.py`).

- **Developer 2 (Risk & Compliance):**
  - Design the Risk Questionnaire logic (`risk_svc.py`).
  - Define the framework mappings (EU AI Act & NIST) in `config/settings.py`.
  - Build `compliance_svc.py` and the respective UIs (`3_Risk_Setup.py`, `4_Compliance.py`).

- **Developer 3 (Monitoring & Reporting):**
  - Build the metrics ingestion and threshold checking logic (`monitoring_svc.py`).
  - Develop the charts and dashboards (`5_Monitoring.py`, `1_Dashboard.py`).
  - Build the `report_gen.py` functionality.

- **Integration Responsibilities (All Hands - Thursday):**
  - Ensure `monitoring_svc` correctly triggers the status updates managed by Dev 1.
  - Ensure Dev 2's risk tiers correctly seed Dev 1's system records.
  - Pair program the "Golden Thread" walkthrough to ensure a flawless demo.

**Suggested Timeline (3-Day Sprint):**
- **Wednesday (Foundation & Core Setup):**
  - Complete shared data model agreement, database setup (`db_manager.py`), and seeding of sample systems (`seed_data.py`).
  - Scaffolding of the multi-page Streamlit application (`app.py`, `1_Dashboard.py`, `2_Inventory.py`).
  - Implement risk engine logic and UI questionnaire (`risk_svc.py`, `3_Risk_Setup.py`).
- **Thursday (Compliance, Monitoring & Integration):**
  - Implement compliance framework mappings and checklists (`compliance_svc.py`, `4_Compliance.py`).
  - Build operational metrics ingestion/simulation and threshold triggers (`monitoring_svc.py`, `5_Monitoring.py`).
  - Implement "The Golden Thread" integration: automate status degradation and append-only audit logging upon threshold breach.
- **Friday (Reporting, Polish & Walkthrough):**
  - Complete PDF report generation backend (`report_gen.py`) and UI export trigger.
  - Final UI polishing (applying custom CSS, glassmorphism, responsive adjustments).
  - Walkthrough verification, end-to-end testing, and demo rehearsal.

---

## STEP 8: MVP Roadmap

**Must Have (MVP for Friday):**
- Shared SQLite data model (The Foundation).
- System inventory (View/Add).
- Risk questionnaire mapping to EU AI Act tiers.
- Compliance checklist with completeness score.
- Metric ingestion with threshold triggers.
- Automated compliance status degradation on breach.
- Append-only audit log.
- Direct PDF report export (via ReportLab).

**Good to Have (If time permits Thursday/Friday):**
- Real CSV upload for metrics (instead of just simulation).
- Visual time-series charts for monitoring metrics.
- High-level portfolio dashboard showing total compliant vs non-compliant systems.

**Stretch Features (Post-MVP):**
- LLM-powered assistant recommending risk tiers based on a plain-language system description.
- Role-based views (Engineer sees metrics, Compliance Officer sees checklists).

---

## STEP 9: Implementation Sequence

Once this plan is approved, We will begin execution in the following sequence:

1. **Phase 1: Foundation (Database & Structure)**
   - Initialize the `governai/` directory structure.
   - Create `database/db_manager.py` and implement the table schemas.
2. **Phase 2: Core Services & Seed Data**
    - Implement backend services (`ai_system_svc.py`, `audit_svc.py`).
    - Implement `seed_data.py` to populate the database with the sample systems (Resume Screening AI, Loan Approval AI, Customer Support Assistant, Meeting Scheduling Agent).
3. **Phase 3: Streamlit UI Framework**
   - Setup `app.py` and create the basic multipage navigation structure.
   - Build the System Inventory views.
4. **Phase 4: Risk & Compliance Modules**
   - Implement `risk_svc.py` and `compliance_svc.py`.
   - Build the UI pages for Risk Setup and Compliance Mapping.
5. **Phase 5: Monitoring & Integration (The Cross-Wiring)**
   - Implement `monitoring_svc.py` with threshold logic.
   - Ensure a metric breach accurately updates the AI system's compliance status and logs to the audit trail.
   - Build the Monitoring dashboard UI.
6. **Phase 6: Reporting & Review**
   - Implement `report_gen.py`.
   - Run end-to-end tests to verify the "Golden Thread" walkthrough works perfectly.
