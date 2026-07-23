# GovernAI Setup & Run Guide
### Microsoft Foundry Local (Phi-4-mini-instruct-generic-cpu:5) + Kiji Privacy Proxy

This guide walks you through setting up and running the entire **GovernAI** application stack. It includes setting up the database, local LLM inference, PII masking with Kiji Proxy, and launching the services.

---

## 📋 Prerequisites

Before starting, ensure you have the following installed on your host Windows machine:
- **Windows 10 or 11** (with Administrator access)
- **Python 3.10 or 3.11** installed and added to Windows PATH
- **Git**
- **VS Code** (or your preferred IDE)
- At least **10 GB** of free disk space

---

## 🔧 Step-by-Step Setup

### Step 1: Clone and Configure Environment

1. Navigate to the project root:
   ```powershell
   cd G:\BEINEX.AI\GovernAI
   ```
2. Create your local environment configuration file:
   Copy the contents of the `.env` template if not already present. Verify your `.env` contains the correct database URL and model configuration:
   ```env
   # --- Database -----------------------------------------------------------
   DATABASE_URL=postgresql+psycopg://<username>:<password>@<host>:<port>/<database>

   # --- LLM-powered Risk Tier Suggestion (Foundry Local) --------------------
   FOUNDRY_MODEL_ALIAS=Phi-4-mini-instruct-generic-cpu:5
   FOUNDRY_BASE_URL=http://127.0.0.1:60247/v1
   FOUNDRY_API_KEY=not-required-for-local-use

   # --- OpenAI API Key (Required for GPT-based evaluations) -----------------
   OPENAI_API_KEY=sk-proj-...
   ```

### Step 2: Install Python Dependencies

Open a Windows PowerShell terminal at the project root and run:
```powershell
pip install -r requirements.txt
```
> [!NOTE]
> This installs core dependencies like `streamlit`, `fastapi`, `uvicorn`, `pypdf`, and the legacy `foundry-local-sdk==0.5.1` needed for local CPU-friendly inference.

### Step 3: Initialize the Database Schema

Before running the application, you must initialize the database tables in your configured PostgreSQL/Supabase database. Run:
```powershell
python governai/database/init_db.py
```
This script connects to your `DATABASE_URL` and creates all necessary tables.

### Step 4: Install and Start Microsoft Foundry Local

1. Install **Foundry Local** via Windows Package Manager:
   ```powershell
   winget install -e --id Microsoft.FoundryLocal
   ```
2. Restart your terminal to refresh path variables.
3. Start the local inference service:
   ```powershell
   foundry service start
   ```
4. Download and run the **Phi-4** model:
   ```powershell
   foundry model run Phi-4-mini-instruct-generic-cpu:5
   ```
5. Verify the model is downloaded and active:
   ```powershell
   foundry model list
   ```

---

## 🔒 Step 5: WSL & Kiji Privacy Proxy Setup

The **Kiji Privacy Proxy** runs on WSL (Ubuntu) to redact PII (names, emails, SSNs) from inputs before sending them to the LLM.

### 1. Install WSL and Ubuntu (if not already done)
Open PowerShell as Administrator and run:
```powershell
wsl --install
wsl --install -d Ubuntu
```
Restart your computer if prompted. Set up your Linux username and password when Ubuntu launches.

### 2. Install Kiji Proxy
Open a **WSL/Ubuntu terminal** and run the following commands:
```bash
# Clone the repository to your WSL home directory
cd ~
git clone https://github.com/dataiku/kiji-proxy.git
cd kiji-proxy

# Download the Kiji Debian package from GitHub Releases (v1.3.1)
# You can copy it from your Windows Downloads folder if downloaded via browser:
sudo dpkg -i /mnt/c/Users/<WindowsUsername>/Downloads/kiji-privacy-proxy_1.3.1_amd64.deb

# If you get dependency errors, fix them and retry:
sudo apt-get install -f
sudo dpkg -i /mnt/c/Users/<WindowsUsername>/Downloads/kiji-privacy-proxy_1.3.1_amd64.deb

# Link Kiji's native ONNX libraries to your home repository folder
ln -sf /opt/kiji-privacy-proxy/lib lib
```

### 3. Run Kiji Proxy
Every time you want to use the proxy, run this in your WSL terminal:
```bash
kiji-proxy
```
> [!IMPORTANT]
> Keep this terminal open. It runs the proxy on port `8080` (REST API) and port `8081` (Transparent Proxy).

---

## 🚀 How to Run the Applications

You can run the entire GovernAI stack automatically using PowerShell scripts or manually by launching individual terminals.

### Method A: Using the Automated Script (Recommended)

1. Open a single **Windows PowerShell** terminal at the project root.
2. Launch the entire application stack:
   ```powershell
   .\start.ps1
   ```
   This script starts:
   - **FastAPI Intake API** (Port 8000)
   - **GovernAI Dashboard** (Port 8501)
   - **HR Resume Screener** (Port 8502)
   All background services log their stdout/stderr output into the `./logs/` folder.

3. To cleanly shut down all services, run:
   ```powershell
   .\stop.ps1
   ```

### Method B: Manual Service Startup

If you prefer to debug or run services in separate terminals, open **3 Windows PowerShell terminals**:

* **Terminal 1: FastAPI Intake API**
  ```powershell
  cd G:\BEINEX.AI\GovernAI\governai
  uvicorn api.server:app --reload --port 8000
  ```
* **Terminal 2: GovernAI Dashboard**
  ```powershell
  cd G:\BEINEX.AI\GovernAI
  streamlit run governai/Home.py --server.port 8501
  ```
* **Terminal 3: HR Resume Screener App**
  ```powershell
  cd G:\BEINEX.AI\GovernAI
  streamlit run resume_screener_app.py --server.port 8502
  ```

---

## 🔍 Verification & Demonstration

1. Make sure **Kiji Proxy** is running in WSL.
2. Open the **HR Resume Screener** at `http://localhost:8502`.
3. Choose a job profile (e.g., *Python Backend Engineer*).
4. Upload a test PDF resume containing placeholder names or contact details.
5. Click **Evaluate Candidate**. The screen will show:
   - The redacted text (names/emails replaced).
   - The LLM score, selection decision, and justification.
   - Status confirmation that the event was pushed to the GovernAI Intake API.
6. Open the **GovernAI Dashboard** at `http://localhost:8501` to view the new system registered, its active status (live heartbeats), compliance status, and telemetry history.

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `streamlit: command not found` | Python environment not active or streamlit not in PATH | Run `pip install streamlit` and run it from Windows PowerShell. |
| `OperationalError` on DB query | Database schema not initialized | Run `python governai/database/init_db.py` once to set up tables. |
| Kiji Proxy fails with `ONNX library not found` | Symlink to native libraries is missing | Run `ln -sf /opt/kiji-privacy-proxy/lib lib` inside your `~/kiji-proxy` folder. |
| PII is not masked in the Resume Screener | Kiji is offline or regex rules not loaded | Check that `kiji-proxy` is running in WSL. You can load regex rules by posting them to `http://localhost:8080/api/pii/regexes` (see `KIJI_QUICKSTART.md`). |
| Streamlit / FastAPI address conflicts | Ports `8501`, `8502` or `8000` already in use | Run `.\stop.ps1` to kill orphaned processes, or manually end python processes in Task Manager. |
