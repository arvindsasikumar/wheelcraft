@echo off
setlocal
title wheelcraft
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup: creating virtual environment...
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: Python 3.11 not found. Install it from https://www.python.org/downloads/
        echo Make sure to tick "Add to PATH" during install.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency install failed. See errors above.
        pause
        exit /b 1
    )
    echo.
    echo Setup complete.
    echo.
)

echo Starting wheelcraft on http://localhost:8765
echo The browser will open automatically. Ctrl+C in this window to stop.
echo.

.venv\Scripts\python.exe server.py
