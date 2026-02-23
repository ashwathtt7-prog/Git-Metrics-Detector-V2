@echo off
REM Run Metabase using portable JDK (no admin install required)
set MB_JETTY_PORT=3003
setlocal EnableExtensions EnableDelayedExpansion

if not exist "metabase.jar" (
    echo ERROR: metabase.jar not found in backend\
    echo Download it from https://www.metabase.com/start/ and place it as backend\metabase.jar
    pause
    exit /b 1
)

REM Try portable JDK first (backend/jdk-*), then system Java
set "JAVA_EXE=java"
for /d %%D in (jdk-*) do (
    if exist "%%D\\bin\\java.exe" (
        set "JAVA_EXE=%%D\\bin\\java.exe"
        goto :have_java
    )
)
:have_java
if not "!JAVA_EXE!"=="java" (
    echo Using portable JDK: "!JAVA_EXE!"
) else (
    echo Using system Java...
)
"!JAVA_EXE!" -jar metabase.jar
pause
