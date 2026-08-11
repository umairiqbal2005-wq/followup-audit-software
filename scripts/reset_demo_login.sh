#!/usr/bin/env bash
# Reset local SQLite DB and restart stack so demo logins work.
# Usage: ./scripts/reset_demo_login.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Stopping containers and removing demo DB volume..."
docker compose down -v 2>/dev/null || true
rm -f backend/aop.db backend/test_aop.db

echo "Starting stack..."
docker compose up -d --build

echo
echo "Login with:"
echo "  admin / demo123"
echo "  umair / demo123"
echo
echo "App: http://localhost:3000"
echo "API: http://localhost:8000/docs"
