@echo off
REM Start all services for Git Metrics Detector
setlocal EnableExtensions EnableDelayedExpansion
echo ============================================
echo   Git Metrics Detector - Starting Services
echo ============================================

REM 1. Start Backend (FastAPI)
echo.
echo [1/4] Starting Backend (port 8001)...
cd backend
start "Backend" cmd /k "cd /d %~dp0backend && if not exist venv\\Scripts\\python.exe (python -m venv venv) && call venv\\Scripts\\activate.bat && if not exist venv\\.deps_installed (pip install -r requirements.txt && type nul > venv\\.deps_installed) && if not exist .env (copy .env.example .env) && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
cd ..

REM 2. Start Workflow Frontend (Vite)
echo [2/4] Starting Workflow Frontend (port 3001)...
cd frontend\workflow
start "Workflow" cmd /k "cd /d %~dp0frontend\\workflow && if not exist node_modules (npm install) && npm run dev -- --host"
cd ..\..

REM 3. Start Dashboard Frontend (Vite)
echo [3/4] Starting Dashboard Frontend (port 3000)...
cd frontend\dashboard
start "Dashboard" cmd /k "cd /d %~dp0frontend\\dashboard && if not exist node_modules (npm install) && npm run dev -- --host"
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
set "JAVA_EXE=java"
for /d %%D in (jdk-*) do (
    if exist "%%D\\bin\\java.exe" (
        set "JAVA_EXE=%%D\\bin\\java.exe"
        goto :have_java
    )
)
:have_java
start "Metabase" cmd /k "set MB_JETTY_PORT=3003 && \"!JAVA_EXE!\" -jar metabase.jar"
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
