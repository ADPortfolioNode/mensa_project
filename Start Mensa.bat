@echo off
cd /d "%~dp0"
call "%~dp0_start_mensa_core.bat" %*
exit /b %ERRORLEVEL%