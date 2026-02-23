@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Git Metrics Detector - Install

echo ============================================
echo   Git Metrics Detector - INSTALL (Windows)
echo ============================================
echo.

REM Prefer the Python launcher if available
set "PY_EXE=python"
set "PY_ARGS="
where py >nul 2>nul
if not errorlevel 1 (
  set "PY_EXE=py"
  set "PY_ARGS=-3"
)

REM Basic check
%PY_EXE% %PY_ARGS% --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3 was not found.
  echo.
  echo Install Python 3.10+ and make sure it is available in PATH, then run Install.bat again.
  echo - Download: https://www.python.org/downloads/
  echo - During install, check: "Add python.exe to PATH"
  echo.
  pause
  exit /b 1
)

echo Running: %PY_EXE% %PY_ARGS% install.py %*
echo.
%PY_EXE% %PY_ARGS% install.py %*
set "EC=%ERRORLEVEL%"
echo.
if not "%EC%"=="0" (
  echo Install failed with exit code %EC%.
  echo.
  echo Common fixes:
  echo - Install Node.js - npm included: https://nodejs.org/
  echo - Install Java 21+ - required for Metabase: https://adoptium.net/temurin/releases/?version=21
  echo - Re-run Install.bat
  echo.
  pause
  exit /b %EC%
)

echo.
echo ============================================
echo   Install complete.
echo   Next: double-click Run.bat
echo ============================================
echo.
pause
exit /b 0
