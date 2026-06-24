# GovernAI Implementation Plan

## Overview

GovernAI is a Streamlit-based AI Governance Platform designed to help organizations inventory, assess, monitor, and govern AI systems throughout their lifecycle.

The platform provides a centralized governance layer that connects risk classification, compliance management, monitoring, and audit reporting into a single workflow.

GovernAI aligns with governance frameworks such as the EU AI Act and NIST AI Risk Management Framework (AI RMF).

---

## Objectives

* Maintain a centralized inventory of AI systems
* Classify AI systems according to risk
* Map systems to compliance requirements
* Monitor responsible AI metrics
* Maintain audit-ready governance records
* Generate governance and compliance reports

---

## Governance Workflow

```text
AI System Registration
        ↓
PII Detection
        ↓
Risk Classification
        ↓
Compliance Mapping
        ↓
Monitoring & Observability
        ↓
Audit Trail
        ↓
Report Generation
```

### Governance Logic

* Risk tier determines applicable compliance requirements.
* Monitoring results influence compliance status.
* Compliance status is reflected in reports.
* All governance actions are recorded in the audit trail.

---

## System Architecture

```text
+--------------------------------------------------+
|                 Streamlit UI                     |
|--------------------------------------------------|
| Inventory | Risk | Compliance | Monitoring       |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|            Governance Services Layer             |
|--------------------------------------------------|
| Inventory Service                                |
| Risk Classification Engine                       |
| Compliance Management Engine                     |
| Monitoring Engine                                |
| Audit Service                                    |
| Reporting Service                                |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|                Shared Governance Data            |
|--------------------------------------------------|
| AI Systems                                       |
| Compliance Records                               |
| Monitoring Metrics                               |
| Audit Logs                                       |
| Evidence Documents                               |
+------------------------+-------------------------+
                         |
                         v
+--------------------------------------------------+
|            Optional AI Assistance Layer          |
|--------------------------------------------------|
| Risk Recommendation                              |
| Compliance Summarization                         |
| Governance Assistant                             |
| Report Narrative Generation                      |
+--------------------------------------------------+
```

The Governance Services Layer acts as the orchestration layer that keeps all modules connected. Changes in one governance domain automatically influence related governance processes.

---

## Suggested Project Structure

```text
governai/
│
├── app.py
│
├── pages/
│   ├── Inventory.py
│   ├── Risk_Assessment.py
│   ├── Compliance.py
│   ├── Monitoring.py
│   └── Reports.py
│
├── services/
│   ├── risk_service.py
│   ├── compliance_service.py
│   ├── monitoring_service.py
│   ├── audit_service.py
│   └── report_service.py
│
├── data/
│   ├── seed_data.py
│   ├── sample_metrics.csv
│   └── governai.db
│
├── ai/
│   ├── governance_assistant.py
│   └── presidio_scanner.py
│
└── README.md
```

### Structure Overview

* **app.py** → Main Streamlit application entry point
* **pages/** → Inventory, Risk Assessment, Compliance, Monitoring, and Reporting pages
* **services/** → Core governance workflows and business logic
* **data/** → SQLite database, seed data, and monitoring datasets
* **ai/** → AI-assisted governance features and PII detection
* **README.md** → Project documentation and implementation plan

---

## Shared Governance Data Model

Each AI system contains:

* System Name
* Owner
* Business Purpose
* Model / Vendor
* Data Sources
* Risk Tier
* Compliance Status
* Monitoring Status
* Evidence & Documentation

This serves as the platform's single source of truth.

---

## Seeded Sample Systems

The platform is initialized with representative AI systems covering multiple governance profiles.

| System                         | Purpose                                      | Risk Tier    |
| ------------------------------ | -------------------------------------------- | ------------ |
| HireIQ – Resume Screener       | Candidate screening and ranking              | High Risk    |
| CreditLens – Loan Scoring      | Credit assessment and approval               | High Risk    |
| AskOps – Internal Chatbot      | Employee support and assistance              | Limited Risk |
| LogSentinel – Anomaly Detector | Operational monitoring and anomaly detection | Minimal Risk |

Sample monitoring data and governance thresholds are preloaded through the seed dataset to demonstrate compliance status changes, monitoring alerts, and audit trail generation during the end-to-end walkthrough.

---

## AI System Onboarding

### Required Information

* System Name
* Owner
* Business Purpose
* Model / Vendor
* Data Sources

### Registration Flow

```text
Add System
      ↓
PII Scan
      ↓
Risk Assessment
      ↓
Risk Tier Assignment
      ↓
Compliance Checklist Generation
      ↓
Monitoring Setup
      ↓
Audit Log Entry
```

The newly registered system becomes part of the governance inventory and can be monitored throughout its lifecycle.

---

## Compliance Framework Coverage

### EU AI Act

* Risk Categorization
* Transparency Requirements
* Human Oversight
* Technical Documentation
* Governance Reporting

### NIST AI RMF

* Govern
* Map
* Measure
* Manage

Future versions may support ISO 42001 and additional governance frameworks.

---

## Monitoring Metrics

GovernAI continuously monitors governance-related indicators.

### Core Metrics

* Model Drift
* Bias & Fairness
* Hallucination Rate
* Cost Monitoring
* Data Freshness

---

## Threshold-Based Governance

Each metric is evaluated against predefined governance thresholds.

### Status Levels

| Condition                   | Governance Status |
| --------------------------- | ----------------- |
| Within Threshold            | Compliant         |
| Warning Threshold Breached  | At Risk           |
| Critical Threshold Breached | Non-Compliant     |

### Governance Actions

Threshold breaches automatically:

* Update compliance status
* Generate audit events
* Appear in governance reports
* Trigger governance review workflows

This ensures monitoring directly influences governance outcomes.

---

## PII Detection

GovernAI integrates Microsoft Presidio for sensitive data detection.

### Detection Scope

* System descriptions
* Business purpose fields
* Uploaded documents
* Governance evidence

### Supported PII Types

* Person Names
* Email Addresses
* Phone Numbers
* Location Information
* National Identifiers

Detected PII is flagged for governance review and recorded as part of the system assessment process.

---

## AI & Model Strategy

The platform supports both cloud-hosted and locally deployed AI models.

### Supported Models

#### GPT-4o / GPT-4o Mini

Used for:

* Governance assistance
* Compliance summaries
* Report generation
* Policy explanations

#### Mistral 7B

Used for:

* Risk classification recommendations
* Governance assistant workflows
* Local deployment scenarios

#### Foundry Local

Supports enterprise deployment of approved open-source models for:

* Privacy-sensitive environments
* On-premise governance workflows
* Offline governance assistance

### AI-Assisted Governance Features

* Risk tier recommendation
* Compliance gap summarization
* Governance Q&A
* Policy explanation
* Audit narrative generation

AI assists governance activities while maintaining human oversight and approval.

---

## Audit & Reporting

### Audit Events

* System creation
* System modification
* Risk classification changes
* Compliance updates
* Threshold breaches
* Evidence uploads

### Reporting

Generated reports include:

* System details
* Risk classification
* Compliance status
* Monitoring results
* Audit history
* Governance evidence

---

## Future Roadmap

Future releases may include:

* Governance Copilot
* Natural Language Compliance Search
* Retrieval-Augmented Governance (RAG)
* Automated Evidence Analysis
* Policy Question Answering
* Multi-Agent Governance Workflows
* Enterprise Knowledge Base Integration
* Portfolio-Wide Risk Dashboard

### Future AI Model Integration

The platform architecture remains model-agnostic and can support:

* GPT-4o
* GPT-4o Mini
* Mistral Family
* Phi Models
* Foundry Local Models
* Enterprise-approved Open Source Models

without requiring changes to the governance workflow.

---

## Development Priority

1. Shared Data Model
2. Inventory Module
3. Risk Classification
4. Compliance Mapping
5. Monitoring & Threshold Logic
6. Audit Trail
7. Report Generation
8. AI-Assisted Governance Features

---

## Key Design Principles

* Single Source of Truth
* Risk-Based Governance
* Explainability
* Auditability
* Human Oversight
* Responsible AI
* Continuous Monitoring
* Scalability

---

## Expected Outcome

GovernAI provides organizations with a centralized platform for managing AI risk, compliance, monitoring, and audit readiness. By connecting inventory, governance, monitoring, and reporting into a single workflow, the platform enables proactive and transparent AI governance.
