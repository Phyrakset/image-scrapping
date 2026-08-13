@echo off
echo ============================================
echo   TverKar Image Scrapping - Setup Script
echo ============================================
echo.

echo [1/4] Activating virtual environment...
call venv\Scripts\activate

echo [2/4] Installing Python dependencies...
pip install -r requirements.txt

echo [3/4] Installing Playwright browser (Chromium)...
playwright install chromium

echo [4/4] Creating .env file if not exists...
if not exist .env (
    copy .env.example .env
    echo Created .env file from template. Please edit it with your API keys.
) else (
    echo .env file already exists, skipping.
)

echo.
echo ============================================
echo   Setup Complete!
echo   Run: python app.py
echo   Open: http://localhost:5000
echo ============================================
pause
