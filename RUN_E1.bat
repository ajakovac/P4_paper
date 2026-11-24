@echo off
setlocal
cd /d "%~dp0"
python runner\run_envelope.py experiment --id E1
set "RC=%ERRORLEVEL%"
echo.
echo ====================================================================
echo Envelope command finished. Exit code: %RC%
echo This window will remain open until you press a key.
echo ====================================================================
pause >nul
exit /b %RC%
