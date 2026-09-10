@echo off
REM SL Booking - Development Setup Script (Windows)

setlocal enabledelayedexpansion

echo.
echo ================================
echo SL Booking - Development Setup
echo ================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11 or higher.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Found: %PYTHON_VERSION%
echo.

REM Check PostgreSQL
echo Checking PostgreSQL installation...
where psql >nul 2>&1
if errorlevel 1 (
    echo WARNING: PostgreSQL not found. Please install PostgreSQL 14 or higher.
) else (
    for /f "tokens=*" %%i in ('psql --version') do set PG_VERSION=%%i
    echo [OK] Found: !PG_VERSION!
)
echo.

REM Check Redis
echo Checking Redis installation...
where redis-cli >nul 2>&1
if errorlevel 1 (
    echo WARNING: Redis not found. Some features may not work without Redis.
) else (
    for /f "tokens=*" %%i in ('redis-cli --version') do set REDIS_VERSION=%%i
    echo [OK] Found: !REDIS_VERSION!
)
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Dependencies installed
echo.

REM Create .env file if it doesn't exist
echo Checking .env file...
if not exist ".env" (
    copy .env.example .env
    echo [OK] Created .env file (update with your settings)
) else (
    echo [OK] .env file already exists
)
echo.

REM Create database
echo Creating PostgreSQL database...
set DB_NAME=slbooking
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '%DB_NAME%'" | findstr 1 >nul
if errorlevel 1 (
    psql -U postgres -c "CREATE DATABASE %DB_NAME%;"
    echo [OK] Database '%DB_NAME%' created
) else (
    echo [OK] Database '%DB_NAME%' already exists
)
echo.

REM Run migrations
echo Running database migrations...
cd backend
python manage.py migrate --settings=config.settings.development
echo [OK] Migrations complete
cd ..
echo.

REM Create logs directory
echo Creating logs directory...
if not exist "backend\logs" (
    mkdir backend\logs
    echo [OK] Logs directory created
) else (
    echo [OK] Logs directory already exists
)
echo.

echo.
echo ================================
echo Setup complete!
echo ================================
echo.
echo Next steps:
echo 1. Update .env file with your settings
echo 2. Start Django: python manage.py runserver --settings=config.settings.development
echo 3. Visit: http://localhost:8000
echo 4. Admin: http://localhost:8000/admin
echo 5. API Docs: http://localhost:8000/api/docs/
echo.
pause
