# Kiji Privacy Proxy — Quick Start (Demo Day)

This is the short version: exact steps to get Kiji running reliably before a demo,
with a sanity check so you know it's actually healthy before you rely on it.

For the *why* behind each fix (ONNX errors, permission issues, regex rules), see
`KIJI_PROXY_IMPLEMENTATION_GUIDE.md` — that doc stays as the full reference.
This doc is just "what do I type, in what order, right now."

---

## One-time setup (already done on this machine)

If you're on a **fresh machine** that's never run Kiji before, do this once:

```bash
cd ~
git clone https://github.com/dataiku/kiji-proxy.git
cd kiji-proxy
ln -sf /opt/kiji-privacy-proxy/lib lib
```

If `kiji-proxy` is already on your PATH (check with `which kiji-proxy`), you can skip this —
it's already installed and linked correctly.

---

## Every time you demo: starting Kiji

Open a **WSL/Ubuntu terminal** and run:

```bash
kiji-proxy
```

### What a healthy start looks like

You should see something close to this in the terminal:

```
Starting Kiji Privacy Proxy service on port :8080
PII detection enabled with ONNX model detector
Using SQLite database at /home/<you>/.kiji-proxy/kiji_privacy_proxy.db
Starting transparent proxy on port :8081
```

If you see `Extracted model file verified` and `[ModelManager] Detector loaded successfully`
somewhere in there too — you're good, PII masking is live.

### A warning you can safely ignore

You'll likely see this line:
```
Warning: Failed to enable system proxy: system proxy configuration only supported on macOS
```
This is expected on WSL/Linux — it does **not** mean Kiji is broken. GovernAI's
`pii_pipeline.py` talks to Kiji directly via its REST API (`localhost:8080/api/pii/check`),
not through the transparent system proxy, so this warning doesn't affect the demo.

---

## Sanity check before your demo starts

Quick manual test to confirm masking is actually working, run from anywhere:

```bash
curl -X POST http://localhost:8080/api/pii/check \
  -H "Content-Type: application/json" \
  -d '{"message": "Contact John Doe at 555-123-4567 or john@example.com"}'
```

You should get back a `masked_message` with the name, phone number, and email redacted.
If it comes back unmasked or you get a connection error, Kiji isn't healthy — see
Troubleshooting below.

---

## Regex rules for strict formats (phone, SSN, credit card, names)

These are stored in Kiji's SQLite DB, so **normally you only need to load them once**
and they persist across restarts. If your sanity check above shows names/numbers
coming through unmasked, reload them:

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

Run this from **Windows PowerShell** (not WSL). If you're demoing with new team member
names not in the `PERSON` pattern, add them to that list before the demo.

---

## Troubleshooting decision tree

| Symptom | Likely cause | Fix |
|---|---|---|
| `cannot open shared object file: libonnxruntime.so` | `lib` symlink missing or broken | Re-run the one-time setup's `ln -sf` step |
| `mkdir model: permission denied` | Running from `/opt/` directly | Always run `kiji-proxy` from `~/kiji-proxy`, never from `/opt/kiji-privacy-proxy` |
| Sanity check returns text unmasked | Regex rules not loaded, or ONNX model not `healthy` | Reload regex rules (above); check startup log for `healthy: false` |
| `curl` connection refused on 8080 | Kiji not running, or crashed silently | Re-run `kiji-proxy` in WSL, watch for errors in the terminal output |
| Streamlit crashes with `OperationalError` on `ai_systems` table | DB not initialized | `python governai/database/init_db.py` (run once, from Windows PowerShell) |

---

*Reference: see `KIJI_PROXY_IMPLEMENTATION_GUIDE.md` for the original root-cause
investigation behind each of these fixes.*
