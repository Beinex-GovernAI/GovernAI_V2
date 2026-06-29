# GovernAI: AI Governance Platform

GovernAI is a centralized portal for managing AI systems, assessing risk against the EU AI Act, mapping compliance controls, and monitoring operational safety in real-time.

## Tech Stack
- **Frontend**: Streamlit
- **Backend/ORM**: Python / SQLAlchemy ORM
- **Database**: PostgreSQL (Hosted on Supabase)
- **Reporting**: ReportLab (Dynamic PDF generation)

---

## 🚀 Getting Started & Local Setup

Follow these steps to run the application on your local machine.

### 1. Clone the Repository
```bash
git clone https://github.com/abhay-beinex/GovernAI.git
cd GovernAI
```

### 2. Install Dependencies
Make sure you have Python installed, then install the required libraries:
```bash
pip install streamlit sqlalchemy psycopg psycopg-binary reportlab pandas python-dotenv
```

### 3. Setup Environment Variables
Since the database is hosted in the cloud (Supabase), you don't need to install PostgreSQL locally! However, you do need the database URL connection string.

1. Create a file named `.env` at the root of the project.
2. Add the following line to it:
```text
DATABASE_URL= #database url
```
*(Note: Keep this `.env` file local. It is already added to `.gitignore` so your database password won't be pushed to GitHub).*

### 4. Run the Streamlit Application
Run the following command from the project root:
```bash
streamlit run governai/app.py
```
This will start a local server and open the app in your default browser at `http://localhost:8501`.

---

## 📂 Project Structure

```text
governai/
├── app.py                 # Main Streamlit entry point (Navigation & Identity Selector)
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
│   └── audit_svc.py       # Append-only logging logic
├── pages/
│   ├── 1_Dashboard.py     # High-level portfolio view
│   ├── 2_Inventory.py     # System inventory & PDF report generator
│   ├── 3_Risk_Setup.py    # Risk assessment questionnaire
│   ├── 4_Compliance.py    # Compliance checklists status tracker
│   └── 5_Monitoring.py    # Operations dashboard and simulation
└── reports/
    └── report_gen.py      # ReportLab PDF generator service
```
