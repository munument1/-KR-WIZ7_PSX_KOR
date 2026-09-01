@echo off
setlocal
set "SCRIPT=%~dp0apply_patch.ps1"
if not exist "%SCRIPT%" (
  echo ERROR: apply_patch.ps1 not found.
  pause
  exit /b 1
)
if "%~1"=="" (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
) else (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" "%~1"
)
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Patch failed. See the error above.
pause
exit /b %RC%
