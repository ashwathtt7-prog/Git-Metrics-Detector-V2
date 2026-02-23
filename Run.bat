@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Git Metrics Detector - Run

echo ============================================
echo   Git Metrics Detector - RUN (Windows)
echo ============================================
echo.
echo Keep this window open while you use the app.
echo Press Ctrl+C here to stop all services.
echo.

REM Debug mode (set GMD_DEBUG=1 before running)
if not "%GMD_DEBUG%"=="" (
  echo on
)

REM Prefer the Python launcher if available
set "PY_EXE=python"
set "PY_ARGS="
where py >nul 2>nul
if not errorlevel 1 (
  set "PY_EXE=py"
  set "PY_ARGS=-3"
)

%PY_EXE% %PY_ARGS% --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3 was not found.
  echo Run Install.bat first and install Python if needed.
  echo.
  pause
  exit /b 1
)

echo Running: %PY_EXE% %PY_ARGS% run.py %*
echo.
%PY_EXE% %PY_ARGS% run.py %*
set "EC=%ERRORLEVEL%"
echo.
if not "%EC%"=="0" (
  echo Run failed with exit code %EC%.
  echo.
  echo If Metabase did not start, check logs\metabase.log
  echo.
  pause
  exit /b %EC%
)

exit /b 0
