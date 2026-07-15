# GovernAI: AI Governance Platform

GovernAI is a centralized portal for managing AI systems, assessing risk against the EU AI Act & NIST AI RMF, mapping compliance controls, and monitoring operational safety in real-time.

## Tech Stack
- **Frontend**: Streamlit
- **Backend/ORM**: Python / SQLAlchemy ORM
- **Database**: PostgreSQL (Hosted on Supabase)
- **Local LLM**: Azure AI Foundry Local
- **PII Masking**: Dataiku Kiji Privacy Proxy
- **Reporting**: ReportLab (Dynamic PDF generation)

---

## 🚀 Getting Started & Local Setup

Follow these steps to run the application on your local machine.

### 1. Clone the Repository
```bash
git clone https://github.com/Beinex-GovernAI/GovernAI_V2.git
cd GovernAI
```

### 2. Install Dependencies
Make sure you have Python installed, then install the required libraries:
```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables
1. Create a file named `.env` at the root of the project (copying from `.env.example`).
2. Add the following lines to it:
```text
DATABASE_URL=your_supabase_database_connection_string

FOUNDRY_MODEL_ALIAS=Phi-3.5-mini-instruct-generic-cpu:2
FOUNDRY_BASE_URL=http://127.0.0.1:<foundry_port>/v1
FOUNDRY_TIMEOUT_SECONDS=60
LLM_MAX_TOKENS=150
LLM_TEMPERATURE=0.1
```
*(Note: Keep this `.env` file local. It is already added to `.gitignore` so your database password won't be pushed to GitHub).*

### 4. Setup Azure AI Foundry Local
The AI-Assisted Tier Suggestion requires a local model running in Microsoft Foundry Local.

1. Ensure WSL (Ubuntu) is installed on your machine.
2. Install Microsoft Foundry Local if you haven't already.
3. Download and start the CPU model:
```bash
foundry model run Phi-3.5-mini-instruct-generic-cpu:2
```
Verify the port Foundry runs on (e.g. by running `foundry service status`) and ensure `FOUNDRY_BASE_URL` in `.env` matches it.

### 5. Setup Kiji Privacy Proxy (Optional but Recommended)
To enable automatic PII masking before sending data to the LLM, you must set up the Kiji Privacy Proxy in WSL. For detailed instructions on installing the proxy, linking the ONNX libraries, and adding Regex rules, please see our dedicated guide: [KIJI_PROXY_IMPLEMENTATION_GUIDE.md](KIJI_PROXY_IMPLEMENTATION_GUIDE.md).

### 6. Run the Streamlit Application
Run the following command from the project root:
```bash
streamlit run governai/Home.py
```
This will start a local server and open the app in your default browser at `http://localhost:8501`.

---

## 📂 Project Structure

```text
governai/
├── Home.py                 # Main Streamlit entry point (Navigation & Identity Selector)
├── database/
│   ├── db.py              # Database connection and session setup
│   ├── models.py          # SQLAlchemy ORM models
│   ├── init_db.py         # Table creation script
│   └── seed_data.py       # Seed data for demo systems
├── services/
│   ├── ai_system_svc.py   # CRUD operations for AI systems
│   ├── compliance_svc.py  # EU AI Act checklists mapping
│   ├── monitoring_svc.py  # Threshold checks and status updates
│   ├── risk_svc.py        # EU AI Act questionnaire logic
│   ├── audit_svc.py       # Append-only logging logic
│   └── llm/               # LLM risk suggester modules
│       ├── foundry_client.py  # Connects to Azure AI Foundry Local API
│       ├── prompt_templates.py # Renders prompt instructions and parses JSON output
│       ├── pii_pipeline.py    # Pipeline runner for preprocessing user input (Kiji proxy)
│       └── risk_suggester.py  # High-level service orchestration
├── pages/
│   ├── 1_Dashboard.py     # High-level portfolio view
│   ├── 2_Inventory.py     # System inventory & PDF report generator
│   ├── 3_Risk_Setup.py    # Risk assessment questionnaire (with LLM Beta Suggester)
│   ├── 4_Compliance.py    # Compliance checklists status tracker
│   └── 5_Monitoring.py    # Operations dashboard and simulation
└── reports/
    └── report_gen.py      # ReportLab PDF generator service
```
