# GovernAI - Project Overview & Task Distribution

Hey team! 

To get us moving fast and avoid merge conflicts later, I went ahead and set up the foundational architecture for our project. I've created the GitHub repository, set up a live Cloud PostgreSQL database (on Supabase), and built the basic working "skeleton" of the Streamlit app. 

Before we divide up the remaining work, here is a quick breakdown of what the platform actually does and what each page means, so we are all on the same page.

## What is GovernAI?
GovernAI is a platform for companies to register, track, and monitor their Artificial Intelligence systems. The goal is to make sure none of the company's AI tools are biased, drifting, or breaking laws (like the EU AI Act).

### Here is how the app flows page-by-page:

* **1. Dashboard:** This is the executive summary. It shows a quick count of how many AI systems the company owns and how many are currently "Compliant", "At Risk", or "Non-Compliant".
* **2. Inventory:** This is the central registry. If the company builds a new AI (like a Customer Support Chatbot), we register it here. We record who owns it, what its purpose is, and if it uses sensitive data (PII). There is also a button here to export a PDF Audit Report for that system.
* **3. Risk Setup:** Not all AI is dangerous. This page is a questionnaire based on the EU AI Act. By answering the questions for a specific AI system, the app calculates its "Risk Tier" (Minimal, Limited, High, or Prohibited). 
* **4. Compliance:** Once an AI has a Risk Tier, it gets a checklist of rules it must follow. A "High Risk" system will have strict rules (like human oversight required), whereas a "Minimal Risk" system won't have many rules. This page is where users check off those rules and provide evidence.
* **5. Monitoring:** This is the live heartbeat of the AI. We track metrics like "Drift" (is the AI getting dumber?) and "Bias". **The coolest part of our app:** If a metric gets too high and breaches a threshold, our app *automatically* changes the system's status to "Non-Compliant" and records the breach in the Audit Trail. 

---

## 🛠️ How to Run the App on Your Device

Since I set up a shared live cloud database, you don't need to install PostgreSQL locally! The tables and sample data are already created online. You just need to configure the connection:

### 1. Clone the Repo
Open your terminal and run:
```bash
git clone https://github.com/abhay-beinex/GovernAI.git
cd GovernAI
```

### 2. Install Python Dependencies
```bash
pip install streamlit sqlalchemy psycopg psycopg-binary reportlab pandas python-dotenv
```

### 3. Create a Local `.env` File
At the root of the cloned `GovernAI` folder, create a file named `.env` and paste this exact database connection string:
```text
DATABASE_URL=postgresql+psycopg://postgres.mbnogucwazwgadsbcmvx:Unemployment%4020026@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
```

### 4. Launch the App
```bash
streamlit run governai/app.py
```
This will open the app automatically in your browser at `http://localhost:8501`.

---

## Next Steps & Task Distribution

Because I laid out the foundation, the app works end-to-end, but it is very basic. Now we need to divide and conquer to flesh out the actual features and make it look amazing. Here is the proposed task breakdown for the next two days:

### 👩‍💻 Aleena: Risk & Compliance Engine
**Goal:** Make our risk assessment and compliance mapping realistic and comprehensive.
* **Task 1 (Risk Questionnaire):** Right now, `pages/3_Risk_Setup.py` only has 3 basic questions. We need to expand this to at least 7-10 realistic questions based on the EU AI Act.
* **Task 2 (NIST Integration):** Currently, `pages/4_Compliance.py` only generates EU AI Act controls. We need to add a second framework (NIST AI RMF) and show how controls map across both.
* **Task 3 (UI Polish):** Improve the layout of your pages by adding better Streamlit columns, tooltips for the questions, and progress bars for the checklists.

### 👩‍💻 Grishma: Monitoring Dashboard & Data Ingestion
**Goal:** Make the platform visually impressive and handle real data.
* **Task 1 (Visual Charts):** The current dashboard (`pages/1_Dashboard.py`) is just a basic text table. We need to implement `plotly` or `altair` to show beautiful visual charts (e.g., a pie chart of compliant vs non-compliant systems).
* **Task 2 (CSV Upload):** In `pages/5_Monitoring.py`, we currently only have a "Simulate" button for metrics. We need to add a file uploader (`st.file_uploader`) so users can upload a CSV of real metrics and have the system parse it.
* **Task 3 (PDF Styling):** The PDF export in `reports/report_gen.py` works, but it looks a bit plain. Add a company logo, better colors, and formatting to the PDF generation.

### 👨‍💻 Abhay (Me): Database Management & Core Integration
**Goal:** Ensure the cloud database runs smoothly and all your components connect perfectly.
* **Task 1 (Cloud DB):** I am managing our Supabase cloud PostgreSQL instance. I will send you both the `.env` connection string so we are all sharing the exact same live database (no one has to install PostgreSQL locally!).
* **Task 2 (The Golden Thread):** I'll ensure that when Grishma's CSV upload triggers a breach, it correctly cascades into Aleena's compliance status and logs to the audit trail securely.
* **Task 3 (Code Reviews & Merges):** I'll handle the GitHub repository merges to make sure our code integrates without breaking.

Let me know if you are both good with this breakdown! Once we agree, we can get started!
