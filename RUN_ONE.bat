@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: RUN_ONE.bat RUN_ID
  echo Example: RUN_ONE.bat 07
  echo.
  echo This window will remain open until you press a key.
  pause >nul
  exit /b 2
)
python runner\run_envelope.py run --run-id %1
set "RC=%ERRORLEVEL%"
echo.
echo ====================================================================
echo Envelope command finished. Exit code: %RC%
echo This window will remain open until you press a key.
echo ====================================================================
pause >nul
exit /b %RC%
