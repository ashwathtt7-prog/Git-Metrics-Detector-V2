@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Git Metrics Detector - Portable Install

echo ============================================
echo   Git Metrics Detector - PORTABLE INSTALL
echo ============================================
echo.
echo This script will download and set up everything
echo needed to run the project without admin rights.
echo.

REM Create portable directory
set "PORTABLE_DIR=%~dp0portable"
if not exist "%PORTABLE_DIR%" mkdir "%PORTABLE_DIR%"

REM ============================================
REM Step 1: Check for or download Python
REM ============================================
echo [1/4] Checking Python...

REM First check if we already have portable Python
set "PORTABLE_PYTHON=%PORTABLE_DIR%\python\python.exe"
if exist "%PORTABLE_PYTHON%" (
    echo   Found portable Python: %PORTABLE_PYTHON%
    set "PY_EXE=%PORTABLE_PYTHON%"
    goto :python_ok
)

REM Check system Python
where python >nul 2>nul
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where python') do set "SYS_PYTHON=%%i"
    python --version 2>nul | findstr /R "3\.1[0-9]" >nul
    if not errorlevel 1 (
        echo   Found system Python 3.10+: !SYS_PYTHON!
        set "PY_EXE=!SYS_PYTHON!"
        goto :python_ok
    )
)

REM Check py launcher
where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version 2>nul | findstr /R "3\.1[0-9]" >nul
    if not errorlevel 1 (
        echo   Found Python via py launcher
        set "PY_EXE=py"
        set "PY_ARGS=-3"
        goto :python_ok
    )
)

REM Download portable Python
echo   Python 3.10+ not found. Downloading portable Python...
echo   This may take a few minutes...

set "PYTHON_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
set "PYTHON_ZIP=%PORTABLE_DIR%\python.zip"
set "PYTHON_DIR=%PORTABLE_DIR%\python"

if not exist "%PYTHON_ZIP%" (
    echo   Downloading: %PYTHON_URL%
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing"
    if errorlevel 1 (
        echo   ERROR: Failed to download Python.
        echo   Please install Python 3.10+ manually from https://www.python.org/downloads/
        echo   Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"
echo   Extracting Python...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

REM Configure embedded Python to use pip
echo   Configuring Python...
(
echo import sys
echo sys.path = ['', 'Lib', 'Lib/site-packages', 'python312.zip', '.']
) > "%PYTHON_DIR%\python312._pth"

REM Download get-pip.py
if not exist "%PYTHON_DIR%\get-pip.py" (
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py' -UseBasicParsing"
    "%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
)

set "PY_EXE=%PYTHON_DIR%\python.exe"
set "PY_ARGS="

:python_ok
echo   Using Python: %PY_EXE%

REM ============================================
REM Step 2: Check for or download Node.js
REM ============================================
echo.
echo [2/4] Checking Node.js...

set "PORTABLE_NODE=%PORTABLE_DIR%\node\node.exe"
if exist "%PORTABLE_NODE%" (
    echo   Found portable Node.js: %PORTABLE_NODE%
    set "NODE_DIR=%PORTABLE_DIR%\node"
    set "PATH=%NODE_DIR%;%PATH%"
    goto :node_ok
)

where node >nul 2>nul
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where node') do set "SYS_NODE=%%i"
    echo   Found system Node.js: !SYS_NODE!
    goto :node_ok
)

REM Download portable Node.js
echo   Node.js not found. Downloading portable Node.js...
echo   This may take a few minutes...

set "NODE_URL=https://nodejs.org/dist/v22.12.0/node-v22.12.0-win-x64.zip"
set "NODE_ZIP=%PORTABLE_DIR%\node.zip"
set "NODE_DIR=%PORTABLE_DIR%\node"

if not exist "%NODE_ZIP%" (
    echo   Downloading: %NODE_URL%
    powershell -Command "Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_ZIP%' -UseBasicParsing"
    if errorlevel 1 (
        echo   ERROR: Failed to download Node.js.
        echo   Please install Node.js manually from https://nodejs.org/
        pause
        exit /b 1
    )
)

echo   Extracting Node.js...
powershell -Command "Expand-Archive -Path '%NODE_ZIP%' -DestinationPath '%PORTABLE_DIR%' -Force"

REM Move from node-v22.12.0-win-x64 to node
if exist "%PORTABLE_DIR%\node-v22.12.0-win-x64" (
    if exist "%NODE_DIR%" rd /s /q "%NODE_DIR%"
    move "%PORTABLE_DIR%\node-v22.12.0-win-x64" "%NODE_DIR%" >nul
)

set "PATH=%NODE_DIR%;%PATH%"
echo   Node.js installed at: %NODE_DIR%

:node_ok
echo   Node.js is available.

REM ============================================
REM Step 3: Configure npm for SSL issues
REM ============================================
echo.
echo [3/4] Configuring npm...
npm config set strict-ssl false 2>nul
npm config set fetch-retry-mintimeout 20000 2>nul
npm config set fetch-retry-maxtimeout 120000 2>nul
echo   npm configured.

REM ============================================
REM Step 4: Run Python install script
REM ============================================
echo.
echo [4/4] Running install script...
echo.
echo Running: %PY_EXE% %PY_ARGS% install.py --yes --download-jdk %*
echo.

%PY_EXE% %PY_ARGS% install.py --yes --download-jdk %*
set "EC=%ERRORLEVEL%"

echo.
if not "%EC%"=="0" (
    echo Install failed with exit code %EC%.
    echo.
    echo Troubleshooting:
    echo - Check your internet connection
    echo - If SSL errors persist, try: npm config set strict-ssl false
    echo - Check logs in the 'logs' folder
    echo.
    pause
    exit /b %EC%
)

echo.
echo ============================================
echo   INSTALL COMPLETE!
echo ============================================
echo.
echo Everything is installed in portable mode.
echo No admin privileges were required.
echo.
echo Next: Double-click Run.bat to start the app.
echo.
pause
exit /b 0
