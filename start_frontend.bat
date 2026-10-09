@echo off
cd /d "%~dp0frontend"
where npm >nul 2>&1
if errorlevel 1 (
  echo Install Node.js LTS to use frontend development mode.
  pause
  exit /b 1
)
if not exist node_modules call npm ci
if errorlevel 1 exit /b 1
call npm run dev
pause
