#!/usr/bin/env bash
# Start the PRISM Engine backend (port 8000) and frontend (port 5173) on macOS/Linux.
# Usage: ./dev.sh   (Ctrl+C stops both)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

(cd "$ROOT/backend" && .venv/bin/python -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
npm run dev
