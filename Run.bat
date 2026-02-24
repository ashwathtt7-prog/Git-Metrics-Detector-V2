@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Git Metrics Detector - Run

echo ============================================
echo   Git Metrics Detector - RUN (Windows)
echo ============================================
echo.
echo Keep this window open while you use the app.
echo Press Ctrl+C here to stop all services.
echo.

REM ============================================
REM Setup portable environment
REM ============================================
set "PORTABLE_DIR=%~dp0portable"

REM Add portable Node.js to PATH if it exists
if exist "%PORTABLE_DIR%\node\node.exe" (
    set "PATH=%PORTABLE_DIR%\node;%PATH%"
    echo Using portable Node.js from: %PORTABLE_DIR%\node
)

REM Find Python - prefer portable, then system
set "PY_EXE="
set "PY_ARGS="

if exist "%PORTABLE_DIR%\python\python.exe" (
    set "PY_EXE=%PORTABLE_DIR%\python\python.exe"
    echo Using portable Python from: %PORTABLE_DIR%\python
) else (
    REM Check system Python (skip Windows Store aliases)
    where python >nul 2>nul
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('where python 2^>nul') do (
            set "TEST_PYTHON=%%i"
            REM Skip Windows Store aliases (they don't work)
            echo !TEST_PYTHON! | findstr /I "WindowsApps" >nul
            if errorlevel 1 (
                REM Not a Windows Store alias, test if it actually works
                "!TEST_PYTHON!" --version 2>nul | findstr /R "3\.[1-9][0-9]" >nul
                if not errorlevel 1 (
                    set "PY_EXE=!TEST_PYTHON!"
                )
            )
        )
    )
    
    REM Check py launcher
    if not defined PY_EXE (
        where py >nul 2>nul
        if not errorlevel 1 (
            py -3 --version 2>nul | findstr /R "3\.[1-9][0-9]" >nul
            if not errorlevel 1 (
                set "PY_EXE=py"
                set "PY_ARGS=-3"
            )
        )
    )
)

if not defined PY_EXE (
    echo ERROR: Python 3.10+ was not found.
    echo.
    echo Run Install.bat first - it will download Python automatically.
    echo.
    pause
    exit /b 1
)

REM ============================================
REM Verify installation exists
REM ============================================
if not exist "backend\venv\Scripts\python.exe" (
    if not exist "backend\venv\bin\python" (
        echo ERROR: Virtual environment not found.
        echo Please run Install.bat first.
        echo.
        pause
        exit /b 1
    )
)

if not exist "backend\.env" (
    echo ERROR: backend/.env not found.
    echo Please run Install.bat first.
    echo.
    pause
    exit /b 1
)

REM ============================================
REM Run the application
REM ============================================
echo.
echo Starting services...
echo.
echo Running: "%PY_EXE%" %PY_ARGS% run.py %*
echo.

"%PY_EXE%" %PY_ARGS% run.py %*
set "EC=%ERRORLEVEL%"

echo.
if not "%EC%"=="0" (
    echo Run failed with exit code %EC%.
    echo.
    echo Troubleshooting:
    echo - Check logs\metabase.log for Metabase issues
    echo - Ensure ports 3000, 3001, 8001, 3003 are not in use
    echo - Run Install.bat again if dependencies are missing
    echo.
    pause
    exit /b %EC%
)

exit /b 0
