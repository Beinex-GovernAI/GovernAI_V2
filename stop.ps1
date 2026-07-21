# GovernAI — Stop App Stack (PowerShell)
# Stops FastAPI, Dashboard, and Screener processes started by start.ps1.
# Does NOT stop Kiji — stop that manually in its WSL terminal (Ctrl+C).

Write-Host "Stopping GovernAI app stack..." -ForegroundColor Cyan

Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[ok] All python processes stopped (uvicorn + streamlit apps)"

Write-Host ""
Write-Host "Reminder: Kiji Privacy Proxy is separate — stop it with Ctrl+C in its WSL terminal." -ForegroundColor Yellow
Write-Host "Done."
