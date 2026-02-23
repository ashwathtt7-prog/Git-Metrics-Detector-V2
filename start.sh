#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Git Metrics Detector - Starting Services"
echo "============================================"
echo ""

# --- Backend ---
echo "[1/4] Starting FastAPI backend on port 8001..."
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

python -m uvicorn app.main:app --reload --port 8001 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"
sleep 2

# --- Workflow Frontend ---
echo "[2/4] Starting Workflow app on port 3001..."
cd "$SCRIPT_DIR/frontend/workflow"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
WORKFLOW_PID=$!

# --- Dashboard Frontend ---
echo "[3/4] Starting Workspaces app on port 3000..."
cd "$SCRIPT_DIR/frontend/dashboard"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
DASHBOARD_PID=$!

# --- Metabase (optional) ---
echo "[4/4] Starting Metabase on port 3003 (optional)..."
MB_PID=""
cd "$SCRIPT_DIR/backend"
if [ -f "metabase.jar" ]; then
    JAVA_BIN="java"
    for d in "$SCRIPT_DIR/backend"/jdk-*; do
        if [ -x "$d/bin/java" ]; then
            JAVA_BIN="$d/bin/java"
            break
        fi
    done

    if command -v "$JAVA_BIN" >/dev/null 2>&1; then
        java_version="$("$JAVA_BIN" -version 2>&1 | head -n 1)"
        major=""
        if [[ "$java_version" =~ \"([0-9]+)\. ]]; then
            major="${BASH_REMATCH[1]}"
        elif [[ "$java_version" =~ \"([0-9]+) ]]; then
            major="${BASH_REMATCH[1]}"
        fi

        if [ -n "$major" ] && [ "$major" -lt 21 ]; then
            echo "  Skipping Metabase: Java 21+ required. Detected: $java_version"
        else
            MB_JETTY_PORT=3003 "$JAVA_BIN" -jar metabase.jar &
            MB_PID=$!
            echo "  Metabase PID: $MB_PID"
        fi
    else
        echo "  Skipping Metabase: java not found (install Java 21+ or unpack a portable JDK under backend/jdk-*)."
    fi
else
    echo "  Skipping Metabase: backend/metabase.jar not found."
fi

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

# Trap Ctrl+C to kill all background processes
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID $WORKFLOW_PID $DASHBOARD_PID 2>/dev/null || true
    if [ -n "$MB_PID" ]; then
        kill $MB_PID 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

wait
