@echo off
echo ====================================================================
echo                 FinSight Local Server Startup
echo ====================================================================
echo.

:: Check if backend virtual environment exists
if not exist backend\venv (
    echo [WARNING] Backend virtual environment was not found.
    echo Please run 'setup-local.bat' first to install all dependencies.
    echo.
    pause
    exit /b 1
)

:: Check if Docker daemon is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon is not running!
    echo Please start Docker Desktop and try again.
    echo (Docker is required to run the PostgreSQL database).
    echo.
    pause
    exit /b 1
)

:: 1. Start the DB in Docker (detached)
echo [1/3] Starting PostgreSQL database container...
docker compose up -d db
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start PostgreSQL database container.
    pause
    exit /b 1
)
echo Database is running.

:: 2. Start Backend FastAPI
echo [2/3] Starting FastAPI Backend server in a new window...
start "FinSight Backend" cmd /k "cd backend && call venv\Scripts\activate && echo Starting FastAPI Backend on http://127.0.0.1:8000 ... && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: 3. Start Frontend Next.js
echo [3/3] Starting Next.js Frontend server in a new window...
start "FinSight Frontend" cmd /k "cd frontend && echo Starting Next.js Frontend on http://localhost:3000 ... && npm run dev"

echo.
echo ====================================================================
echo FINSIGHT IS RUNNING!
echo.
echo - Frontend:  http://localhost:3000
echo - Backend:   http://127.0.0.1:8000
echo - API Docs:  http://127.0.0.1:8000/docs
echo.
echo Keep these terminal windows open. To stop the database later, run:
echo    docker compose down
echo ====================================================================
echo.
pause
