@echo off
setlocal EnableExtensions
title Mensa Lottery AI - Starting

cd /d "%~dp0"
if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml not found.
    echo Please run this file from the mensa_project folder.
    goto :fail
)

echo.
echo ============================================================
echo   Mensa Lottery AI - Starting
echo ============================================================
echo.

if exist ".env" (
    echo [OK] Using your existing .env file ^(unchanged^).
) else (
    if not exist ".env.example" (
        echo [ERROR] .env.example is missing. Cannot create .env.
        goto :fail
    )
    echo [SETUP] First-time install: creating .env from .env.example ...
    copy /Y ".env.example" ".env" >nul
    if errorlevel 1 (
        echo [ERROR] Could not create .env
        goto :fail
    )
    echo.
    echo  A new .env file was created. Add API keys for AI chat if you want
    echo  the concierge features. Training and suggestions work without keys.
    echo.
    echo  Opening .env in Notepad - save and close when done, then press any
    echo  key here to continue starting Mensa.
    echo.
    notepad ".env"
    pause >nul
)

echo.
echo [START] Docker check and stack startup via PowerShell ...
echo         ^(first run may take 10-20 minutes^)
echo.

if not exist "%~dp0start-windows.ps1" (
    echo [ERROR] Missing start-windows.ps1 in %~dp0
    goto :fail
)
where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell is not on your PATH.
    goto :fail
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1" -Build -OpenBrowser
if errorlevel 1 (
    echo.
    echo [ERROR] Startup did not complete successfully.
    echo Try: start Docker Desktop manually, wait until it is running,
    echo then run startmensa.bat again. Or run: recover_stack.ps1
    goto :fail
)

echo.
echo ============================================================
echo   Mensa is running. Your browser should open automatically.
echo   If not, open:  http://127.0.0.1:3000
echo   To stop:      StopMensa.bat
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1