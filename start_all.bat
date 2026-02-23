@echo off
REM Start all services for Git Metrics Detector
echo ============================================
echo   Git Metrics Detector - Starting Services
echo ============================================

REM 1. Start Backend (FastAPI)
echo.
echo [1/4] Starting Backend (port 8001)...
cd backend
start "Backend" cmd /k "call venv\\Scripts\\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
cd ..

REM 2. Start Workflow Frontend (Vite)
echo [2/4] Starting Workflow Frontend (port 3001)...
cd frontend\workflow
start "Workflow" cmd /k "npx vite --port 3001"
cd ..\..

REM 3. Start Dashboard Frontend (Vite)
echo [3/4] Starting Dashboard Frontend (port 3000)...
cd frontend\dashboard
start "Dashboard" cmd /k "npx vite --port 3000"
cd ..\..

REM 4. Start Metabase
echo [4/4] Starting Metabase (port 3003)...
cd backend
if not exist "metabase.jar" (
    echo Metabase not started: backend\metabase.jar not found.
    echo Download it from https://www.metabase.com/start/ and place it in backend\metabase.jar
    cd ..
    goto :after_metabase
)
if exist "jdk-21.0.10+7\bin\java.exe" (
    start "Metabase" cmd /k "set MB_JETTY_PORT=3003 && jdk-21.0.10+7\bin\java.exe -jar metabase.jar"
) else (
    start "Metabase" cmd /k "set MB_JETTY_PORT=3003 && java -jar metabase.jar"
)
cd ..
:after_metabase

echo.
echo ============================================
echo   All services starting!
echo.
echo   Workflow UI:  http://localhost:3001
echo   Dashboard:    http://localhost:3000
echo   Backend API:  http://localhost:8001
echo   Metabase:     http://localhost:3003
echo ============================================
echo.
pause
