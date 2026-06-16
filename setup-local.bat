@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo                 FinSight Local Environment Setup
echo ====================================================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo.
    echo Please install Python 3.12+ from https://www.python.org/downloads/
    echo *IMPORTANT*: Make sure to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check for Node.js / npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm was not found in your system PATH.
    echo.
    echo Please install Node.js v20+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: 1. Backend Setup
echo [1/3] Setting up Python virtual environment in 'backend'...
cd backend
if not exist venv (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create python virtual environment.
        cd ..
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists. Skipping creation.
)

echo.
echo [2/3] Installing Python backend packages...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install backend dependencies.
    cd ..
    pause
    exit /b 1
)
echo Backend dependencies installed successfully.
cd ..

:: 2. Frontend Setup
echo.
echo [3/3] Installing Node.js frontend packages (this may take a minute)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install frontend dependencies.
    cd ..
    pause
    exit /b 1
)
echo Frontend dependencies installed successfully.
cd ..

echo.
echo ====================================================================
echo SETUP COMPLETED SUCCESSFULLY!
echo.
echo Next Steps:
echo 1. Keep Docker running (needed for the PostgreSQL database).
echo 2. Start the local server by running: start-local.bat
echo ====================================================================
echo.
pause
