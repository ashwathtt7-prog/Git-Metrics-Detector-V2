@echo off
REM Run Metabase using portable JDK (no admin install required)
set MB_JETTY_PORT=3003

if not exist "metabase.jar" (
    echo ERROR: metabase.jar not found in backend\
    echo Download it from https://www.metabase.com/start/ and place it as backend\metabase.jar
    pause
    exit /b 1
)

REM Try portable JDK first, then system Java
if exist "jdk-21.0.10+7\bin\java.exe" (
    echo Using portable JDK...
    "jdk-21.0.10+7\bin\java.exe" -jar metabase.jar
) else (
    echo Using system Java...
    java -jar metabase.jar
)
pause
