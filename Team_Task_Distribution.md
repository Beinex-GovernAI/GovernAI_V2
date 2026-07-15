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
streamlit run governai/Home.py
```
This will open the app automatically in your browser at `http://localhost:8501`.

---

## 💻 GitHub Collaboration Workflow (How we avoid breaking code)

To ensure we don't accidentally overwrite each other's code, we will use **Feature Branches**. This means you will do your work on a separate "copy" of the code, and then we merge it into the `main` branch when it's finished.

**Rule #1:** Coordinate in the group chat before you edit a file so two people aren't working on the same file at the same time.

**When you start working:**
1. Always pull the latest code first:
   ```bash
   git checkout main
   git pull origin main
   ```
2. Create a new branch for your specific task (e.g., `aleena/llm-feature`):
   ```bash
   git checkout -b yourname/your-feature
   ```
3. Do your coding, testing, and save your files.
4. Commit your changes:
   ```bash
   git add .
   git commit -m "Added the LLM risk predictor logic"
   ```
5. Push your branch to GitHub:
   ```bash
   git push origin yourname/your-feature
   ```
6. Go to the GitHub website and open a **Pull Request (PR)**. I will review it and click Merge to add it to the main project!

---

## Next Steps & Task Distribution (Backend + Frontend)


### 👩‍💻 Aleena: LLM Integration & Risk Engine
**Goal:** Implement the Mentor's stretch goal (LLM integration) and expand our risk backend logic.
* **Task 1 (Backend/AI):** Build an LLM-powered assistant function. It should take the system's "Business Purpose" text and use an LLM API (like OpenAI) to automatically suggest a Risk Tier.
* **Task 2 (Backend):** Right now, `services/risk_svc.py` only has 3 basic questions. Expand the backend Python logic to include at least 7-10 realistic EU AI Act questions with a proper scoring mechanism.
* **Task 3 (Frontend):** In `pages/3_Risk_Setup.py`, add an "AI Auto-Predict Risk" button that calls your new LLM function and displays the result to the user.

### 👩‍💻 Grishma: Data Ingestion Backend & Multi-Framework Compliance
**Goal:** Expand the backend compliance engine to support multiple frameworks and process real CSV data.
* **Task 1 (Backend):** Currently, the Compliance engine only maps to the "EU AI Act". You need to update `services/compliance_svc.py` to also generate checklists for the **NIST AI RMF framework**.
* **Task 2 (Backend/Data):** In `services/monitoring_svc.py`, write a Python parser that can read an uploaded CSV of drift/bias metrics and loop through them to check for threshold breaches.
* **Task 3 (Frontend):** In `pages/5_Monitoring.py`, replace our basic "Simulate" button with a `st.file_uploader` so users can upload their real metric CSVs to your new backend parser.

### 👨‍💻 Abhay (Me): Database Management & Core Integration
**Goal:** Ensure the cloud database runs smoothly and manage code integrations.
* **Task 1 (Cloud DB & DevOps):** I am managing our Supabase cloud instance. Since we are sharing the database, I will manage any schema changes if you guys need new tables.
* **Task 2 (The Golden Thread):** I'll ensure that when Grishma's new NIST compliance logic is added, it cascades perfectly into the Audit Log and PDF reports.
* **Task 3 (Git Flow Master):** I'll be reviewing your Pull Requests and handling the merges on GitHub so we don't get merge conflicts.

Let me know if you are both good with this breakdown! Once we agree, we can get started!
