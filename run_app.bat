@echo off
echo ========================================
echo    Krishi-Gati - Farmer Market Advisor
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

REM Install/upgrade required packages
echo Installing/checking dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install streamlit folium streamlit-folium pandas geopy requests google-generativeai --quiet

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install packages!
    echo Try running: python -m pip install streamlit folium streamlit-folium pandas geopy
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Starting Krishi-Gati...
echo   Open browser at: http://localhost:8501
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Use python -m streamlit instead of just streamlit
python -m streamlit run app.py --server.port 8501

pause
