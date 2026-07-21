# GovernAI - App Stack Startup Script (PowerShell)
# Launches FastAPI Intake API, GovernAI Dashboard, and HR Resume Screener.
# Kiji Privacy Proxy is NOT started here - run it separately from WSL:
#   wsl kiji-proxy

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"


New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "=== GovernAI App Stack Startup ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Logs: $LogDir"
Write-Host ""
Write-Host "NOTE: Kiji Privacy Proxy is not started by this script." -ForegroundColor Yellow
Write-Host "      Run it separately in a WSL terminal: kiji-proxy" -ForegroundColor Yellow
Write-Host ""

Set-Location $ProjectRoot

Write-Host "[1/3] Starting FastAPI Intake API (port 8000)..."
Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "api.server:app", "--reload", "--port", "8000" `
    -WorkingDirectory (Join-Path $ProjectRoot "governai") `
    -RedirectStandardOutput (Join-Path $LogDir "fastapi.log") `
    -RedirectStandardError (Join-Path $LogDir "fastapi_err.log") `
    -WindowStyle Hidden
Start-Sleep -Seconds 2
Write-Host "      -> http://localhost:8000"

Write-Host "[2/3] Starting GovernAI Dashboard (port 8501)..."
Start-Process -FilePath "python" `
    -ArgumentList "-m", "streamlit", "run", "governai\Home.py", "--server.port", "8501" `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput (Join-Path $LogDir "dashboard.log") `
    -RedirectStandardError (Join-Path $LogDir "dashboard_err.log") `
    -WindowStyle Hidden
Start-Sleep -Seconds 2
Write-Host "      -> http://localhost:8501"

Write-Host "[3/3] Starting HR Resume Screener (port 8502)..."
Start-Process -FilePath "python" `
    -ArgumentList "-m", "streamlit", "run", "resume_screener_app.py", "--server.port", "8502" `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput (Join-Path $LogDir "screener.log") `
    -RedirectStandardError (Join-Path $LogDir "screener_err.log") `
    -WindowStyle Hidden
Start-Sleep -Seconds 2
Write-Host "      -> http://localhost:8502"

Write-Host ""
Write-Host "=== All app services launched ===" -ForegroundColor Green
Write-Host "Dashboard:  http://localhost:8501"
Write-Host "Screener:   http://localhost:8502"
Write-Host "API:        http://localhost:8000/docs"
Write-Host ""
Write-Host "Do not forget Kiji - run in a WSL terminal: kiji-proxy" -ForegroundColor Yellow
Write-Host "To stop everything, run: .\stop.ps1"
