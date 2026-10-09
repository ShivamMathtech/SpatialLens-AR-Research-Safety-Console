@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
if errorlevel 1 goto :failed
.venv\Scripts\python.exe scripts\download_models.py
if errorlevel 1 goto :failed
echo YOLO setup complete. Restart the server before opening a real source.
pause
exit /b 0
:failed
echo AI setup failed. Read the error above. Synthetic demo still works.
pause
exit /b 1
