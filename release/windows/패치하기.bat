@echo off
chcp 65001 >nul
setlocal

set "SCRIPT=%~dp0apply_patch.ps1"
if not exist "%SCRIPT%" (
  echo apply_patch.ps1 파일을 찾을 수 없습니다.
  pause
  exit /b 1
)

if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" "%~1"
)

set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo 패치에 실패했습니다. 위 오류 메시지를 확인하세요.
pause
exit /b %RC%
