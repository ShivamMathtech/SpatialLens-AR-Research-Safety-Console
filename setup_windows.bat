@echo off
setlocal
cd /d "%~dp0"
py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 is required. Install it from python.org with the Python Launcher enabled.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.11 -m venv .venv
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed
echo.
echo Setup complete. Double-click start_demo.bat to launch SpatialLens.
echo The prebuilt interface is included. Node.js is only needed to edit the frontend.
pause
exit /b 0
:failed
echo Setup failed. Check your internet connection and the error above.
pause
exit /b 1
