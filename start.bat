@echo off
echo ============================================
echo   Git Metrics Detector - Starting Services
echo ============================================
echo.

echo [1/4] Starting FastAPI backend on port 8000...
start "Backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak > nul

echo [2/4] Starting Workflow app on port 3000...
start "Workflow" cmd /c "cd /d %~dp0frontend\workflow && npm run dev"

echo [3/4] Starting Dashboard app on port 3001...
start "Dashboard" cmd /c "cd /d %~dp0frontend\dashboard && npm run dev"

echo [4/4] Starting Apache Superset on port 8088...
if exist "%~dp0superset_venv\Scripts\superset.exe" (
    start "Superset" cmd /c "set SUPERSET_CONFIG_PATH=%~dp0superset_config.py && %~dp0superset_venv\Scripts\superset.exe run -p 8088 --with-threads --reload"
    echo       Superset starting...
) else (
    echo       [SKIP] Superset not installed. Run: python setup_superset.py
)

echo.
echo ============================================
echo   All services started!
echo.
echo   Backend:   http://localhost:8000/docs
echo   Workflow:  http://localhost:3000
echo   Dashboard: http://localhost:3001
echo   Superset:  http://localhost:8088 (admin/admin)
echo ============================================
echo.
echo Press any key to close this window...
pause > nul
