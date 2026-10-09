#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
npm run build --prefix frontend
