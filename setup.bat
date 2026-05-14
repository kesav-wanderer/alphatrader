@echo off
echo === AI Invest Setup ===
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv

echo [2/4] Activating venv...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo [4/4] Copying .env template...
if not exist .env (
    copy .env.example .env
    echo .env created — edit it to add Kite API keys when ready
)

echo.
echo === Setup Complete ===
echo To run the dashboard:
echo   venv\Scripts\activate.bat
echo   streamlit run frontend\app.py
echo.
pause
