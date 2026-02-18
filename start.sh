#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Git Metrics Detector - Starting Services"
echo "============================================"
echo ""

# --- Backend ---
echo "[1/3] Starting FastAPI backend on port 8000..."
cd "$SCRIPT_DIR/backend"
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

if [ ! -f ".env" ]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
fi

python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"
sleep 2

# --- Workflow Frontend ---
echo "[2/3] Starting Workflow app on port 3000..."
cd "$SCRIPT_DIR/frontend/workflow"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
WORKFLOW_PID=$!

# --- Dashboard Frontend ---
echo "[3/3] Starting Dashboard app on port 3001..."
cd "$SCRIPT_DIR/frontend/dashboard"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
DASHBOARD_PID=$!

echo ""
echo "============================================"
echo "  All services started!"
echo ""
echo "  Backend:   http://localhost:8000/docs"
echo "  Workflow:  http://localhost:3000"
echo "  Dashboard: http://localhost:3001"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap Ctrl+C to kill all background processes
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID $WORKFLOW_PID $DASHBOARD_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

wait
