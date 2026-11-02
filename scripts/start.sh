#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r backend/requirements.lock
npm ci --prefix frontend
npm run build --prefix frontend
printf '\nEscape Plan: http://escape-plan15.local:8000\nServer endpoint: frontend/src/config.ts (LAN profile).\nAdmin controls use ADMIN_TOKEN when set; otherwise local controls are unlocked.\n\n'
exec .venv/bin/python -m uvicorn escapeplan.server:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 16384
