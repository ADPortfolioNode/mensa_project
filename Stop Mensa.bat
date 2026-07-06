@echo off
REM Backward-compatible launcher (calls StopMensa.bat)
cd /d "%~dp0"
call "%~dp0StopMensa.bat" %*
exit /b %ERRORLEVEL%