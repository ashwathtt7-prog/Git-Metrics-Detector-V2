
@echo off
echo ============================================
echo   Git Metrics Detector - Starting Services
echo ============================================
echo.

echo [1/4] Starting FastAPI backend on port 8000...
start "Backend" cmd /c "cd /d %~dp0backend && call venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak > nul

echo [2/4] Starting Dashboard app on port 3000...
start "Dashboard" cmd /c "cd /d %~dp0frontend\dashboard && npm run dev -- --host"

echo [3/4] Starting Workflow app on port 3001...
start "Workflow" cmd /c "cd /d %~dp0frontend\workflow && npm run dev -- --host"

echo [4/4] Starting Evidence Analytics on port 3002...
if exist "%~dp0evidence" (
    start "Evidence" cmd /c "cd /d %~dp0evidence && npm run dev"
) else (
    echo Evidence folder not found, skipping...
)

echo.
echo ============================================
echo   All services started!
echo.
echo   Backend:    http://localhost:8000/docs
echo   Dashboard:  http://localhost:3000
echo   Workflow:   http://localhost:3001
echo   Evidence:   http://localhost:3002
echo ============================================
echo.
echo Press any key to close this window...
pause > nul
