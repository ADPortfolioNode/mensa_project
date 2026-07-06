@echo off
cd /d "%~dp0"
if not exist "%~dp0_start_mensa_core.bat" (
    echo [ERROR] Missing _start_mensa_core.bat in:
    echo   %~dp0
    echo Update the project folder from git or re-download StartMensa.bat.
    pause
    exit /b 1
)
call "%~dp0_start_mensa_core.bat" %*
exit /b %ERRORLEVEL%