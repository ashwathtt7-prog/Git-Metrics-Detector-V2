#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Git Metrics Detector - Starting ALL"
echo "============================================"
echo ""

# --- Backend ---
echo "[1/4] Starting FastAPI backend on port 8001..."
cd "$SCRIPT_DIR/backend"
if [ ! -d "venv" ]; then
  echo "  Creating virtual environment..."
  python3 -m venv venv
fi
source venv/bin/activate
if [ ! -f "venv/.deps_installed" ]; then
  pip install -r requirements.txt
  : > venv/.deps_installed
fi
if [ ! -f ".env" ]; then
  echo "  Creating .env from .env.example..."
  cp .env.example .env
fi

python -m uvicorn app.main:app --reload --port 8001 &
BACKEND_PID=$!
sleep 2

# --- Workflow Frontend ---
echo "[2/4] Starting Workflow app on port 3001..."
cd "$SCRIPT_DIR/frontend/workflow"
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev -- --host &
WORKFLOW_PID=$!

# --- Dashboard Frontend ---
echo "[3/4] Starting Workspaces app on port 3000..."
cd "$SCRIPT_DIR/frontend/dashboard"
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev -- --host &
DASHBOARD_PID=$!

# --- Metabase (required for this script) ---
echo "[4/4] Starting Metabase on port 3003..."
cd "$SCRIPT_DIR"
if [ ! -f "backend/metabase.jar" ]; then
  echo "ERROR: backend/metabase.jar not found."
  echo "Download it first:"
  echo "  curl -L \"https://downloads.metabase.com/latest/metabase.jar\" -o backend/metabase.jar"
  exit 1
fi

chmod +x backend/run_metabase.sh 2>/dev/null || true
MB_JETTY_PORT=3003 ./backend/run_metabase.sh &
MB_PID=$!
sleep 2

echo ""
echo "============================================"
echo "  All services started!"
echo ""
echo "  Backend:    http://localhost:8001/docs"
echo "  Workflow:   http://localhost:3001"
echo "  Workspaces: http://localhost:3000"
echo "  Metabase:   http://localhost:3003"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services"

cleanup() {
  echo ""
  echo "Stopping services..."
  kill "$BACKEND_PID" "$WORKFLOW_PID" "$DASHBOARD_PID" 2>/dev/null || true
  kill "$MB_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

wait

