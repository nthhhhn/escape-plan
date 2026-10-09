#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r backend/requirements.lock
npm ci --prefix frontend
npm run build --prefix frontend
printf '\nEscape Plan: http://127.0.0.1:8000\nAdmin token is stored in data/admin-token after startup.\n\n'
exec .venv/bin/python -m uvicorn escapeplan.server:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 16384
