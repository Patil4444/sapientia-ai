# Sapientia FastAPI — run before Streamlit if you use Settings → Backend base URL.
# Demo: Terminal 1 → this script. Terminal 2 → streamlit run app.py
# Then in the app Settings set Backend base URL to: http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "Create venv first: python -m venv venv && .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "Starting Sapientia API on http://127.0.0.1:8000"
Write-Host "Health: http://127.0.0.1:8000/api/health"
Write-Host "PDF:  POST http://127.0.0.1:8000/api/reports/incident-pdf"
Write-Host ""

& ".\venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
