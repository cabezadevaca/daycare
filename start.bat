@echo off
cd /d "%~dp0"

if not exist "venv\" (
    echo Virtual environment not found. Run deploy.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Starting Daycare App...
python app.py
