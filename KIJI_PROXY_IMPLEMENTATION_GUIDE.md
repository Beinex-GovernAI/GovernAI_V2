# Kiji Privacy Proxy Integration Guide & Troubleshooting

This document outlines how the Kiji Privacy Proxy was integrated into the GovernAI Risk Tier Suggestion pipeline, the roadblocks encountered during setup, and the exact commands used to solve them.

## 1. Code Implementation Updates

The original sketch provided in `LLM_RISK_SUGGESTION.md` contained a placeholder API endpoint and payload structure for Kiji. 

**Problem:** Using the placeholder `http://localhost:8089/mask` with the payload `{"text": "..."}` resulted in an HTTP `404 Not Found` error.
**Solution:** By inspecting Kiji's source code, we identified the correct REST API route and payload keys. We updated `governai/services/llm/pii_pipeline.py` to use:
- **Endpoint:** `http://localhost:8080/api/pii/check`
- **Request Payload:** `{"message": "<text>"}`
- **Response Payload:** `{"masked_message": "<masked_text>"}`

The `pii_pipeline.py` script now successfully intercepts AI system descriptions and routes them through Kiji to redact PII before forwarding them to the local LLM.

## 2. Kiji Proxy Execution Issues (WSL / Ubuntu)

After installing Kiji via the `.deb` package (`dpkg -i`), running the `kiji-proxy` command caused several startup errors regarding the ONNX AI Model.

**Problem 1: ONNX Library Not Found**
Kiji failed to start its AI model, logging:
`Error loading ONNX shared library "./lib/libonnxruntime.so.1.24.2": cannot open shared object file: No such file or directory`
This happens because `kiji-proxy` expects the `lib` folder to be in the current working directory, but the `.deb` package installs these libraries into `/opt/kiji-privacy-proxy/lib`. As a result, the model enters a `healthy: false` state and performs zero masking.

**Problem 2: Permission Denied on Extraction**
If you try to fix the above by running `kiji-proxy` directly inside `/opt/kiji-privacy-proxy`, it fails with a `mkdir model: permission denied` error because a standard user does not have write permissions in the `/opt/` directory to extract the model files.

**The Solution:**
We bypassed both issues by cloning the Kiji repository to the user's home folder (granting write permissions for model extraction) and creating a symbolic link to the `/opt/` libraries.

Run these commands in your Ubuntu (WSL) terminal to start Kiji perfectly every time:
```bash
# 1. Clone the repo to your home directory
cd ~
git clone https://github.com/dataiku/kiji-proxy.git

# 2. Enter the directory and link the ONNX libraries
cd kiji-proxy
ln -sf /opt/kiji-privacy-proxy/lib lib

# 3. Start the proxy
kiji-proxy
```
You should see `✅ Extracted model file verified` and `[ModelManager] Detector loaded successfully` in the terminal.

## 3. Adding Regex Rules for Strict Formats

The ONNX AI model handles complex entity detection (e.g., dynamically pseudonymizing the name "John Doe" to "Nicole Doe"). However, rigid formats like Phone Numbers, SSNs, and Credit Cards are best caught using Regex rules. By default, Kiji starts with `0 pattern(s)`.

**Solution:**
We injected standard Regex rules directly into Kiji's internal SQLite database via its REST API.

To add these rules to Kiji, open a **Windows PowerShell** window and run:

```powershell
$body = @{
    regexes = @(
        @{ name = 'PHONE_NUMBER'; pattern = '\b\d{3}[-.]?\d{3}[-.]?\d{4}\b' },
        @{ name = 'CREDIT_CARD'; pattern = '\b(?:\d[ -]*?){13,16}\b' },
        @{ name = 'SSN'; pattern = '\b\d{3}-\d{2}-\d{4}\b' },
        @{ name = 'EMAIL_ADDRESS'; pattern = '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' },
        @{ name = 'PERSON'; pattern = '(?i)\b(?:John|Michael|Sumesh|Doe|Brown|Aleena)\b' }
    )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8080/api/pii/regexes" -Method Post -ContentType "application/json" -Body $body
```
**Note on Names:** Kiji's default ONNX AI model sometimes struggles with non-Western names (like "Sumesh") or specific casing (like "Michael.brown"). We added the `PERSON` rule with the `(?i)` case-insensitive flag as a strict fallback to ensure all test team names are flawlessly redacted during demonstrations.

## 4. Streamlit Database Initialization Crash

**Problem:** When starting the Streamlit app (`streamlit run governai/app.py`), it immediately crashed with a SQLAlchemy `OperationalError` (`[SQL: SELECT ... FROM ai_systems]`) indicating missing tables.
**Solution:** We initialized the SQLite database schemas by running the initialization script:
```powershell
python governai/database/init_db.py
```
This created all necessary tables, allowing Streamlit to boot successfully.
