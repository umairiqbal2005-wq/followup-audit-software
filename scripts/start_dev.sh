#!/usr/bin/env bash
# Start AOP backend + frontend for local demo login.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p /tmp/aop-logs

if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -r backend/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

# Fresh demo DB so admin/demo123 always works
rm -f backend/aop.db backend/test_aop.db
cp -n backend/.env.example backend/.env || true

# Kill previous demo processes if any
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite --host" 2>/dev/null || true
sleep 1

echo "Starting API on http://127.0.0.1:8000 ..."
(
  cd backend
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) > /tmp/aop-logs/backend.log 2>&1 &
echo $! > /tmp/aop-logs/backend.pid

echo "Starting UI on http://127.0.0.1:3000 ..."
(
  cd frontend
  npm run dev -- --host 0.0.0.0 --port 3000
) > /tmp/aop-logs/frontend.log 2>&1 &
echo $! > /tmp/aop-logs/frontend.pid

sleep 3
echo
echo "Open:  http://localhost:3000"
echo "API:   http://localhost:8000/docs"
echo "Login: admin / demo123"
echo
echo "Logs:  /tmp/aop-logs/backend.log  /tmp/aop-logs/frontend.log"
