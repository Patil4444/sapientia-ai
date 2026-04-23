#!/usr/bin/env bash
# Sapientia FastAPI — run from repo root context.
# Demo: terminal 1 → ./scripts/run_api.sh   |   terminal 2 → streamlit run app.py
# Settings → Backend base URL: http://127.0.0.1:8000
set -e
cd "$(dirname "$0")/.."
if [[ ! -f venv/bin/python ]]; then
  echo "Create venv: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi
echo "Starting Sapientia API on http://127.0.0.1:8000"
exec ./venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
