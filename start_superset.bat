@echo off
echo ============================================
echo   Starting Apache Superset on port 8088
echo ============================================
echo.

set SUPERSET_CONFIG_PATH=%~dp0superset_config.py
"%~dp0superset_venv\Scripts\superset.exe" run -p 8088 --with-threads --reload
