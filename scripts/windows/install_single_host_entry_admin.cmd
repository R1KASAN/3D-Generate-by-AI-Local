@echo off
setlocal
set "INSTALLER=%~dp0install_single_host_entry.ps1"
set "LOG_DIR=%LOCALAPPDATA%\Local3D\logs"
set "LOG_FILE=%LOG_DIR%\service-install.log"

fltmc >nul 2>&1
if errorlevel 1 (
  echo This command must be run from a PowerShell or Command Prompt opened as Administrator.
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
echo Installing only Local3D-ComfyUI, Local3D-API, Local3D-Web, and Local3D-Caddy...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%INSTALLER%" -Install >"%LOG_FILE%" 2>&1
set "RESULT=%ERRORLEVEL%"
type "%LOG_FILE%"
echo.
echo Installer exit code: %RESULT%
echo Log: %LOG_FILE%
exit /b %RESULT%
