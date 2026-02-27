@echo off
REM =============================================================================
REM Daycare App — Windows Deployment Script
REM =============================================================================
REM This script:
REM   1. Checks for Python 3
REM   2. Creates a virtual environment
REM   3. Installs dependencies
REM   4. Generates self-signed SSL certificates (if OpenSSL available)
REM   5. Initializes the database
REM   6. Seeds an admin user (if none exists)
REM   7. Prints instructions to start the app
REM =============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================
echo   Daycare App - Windows Deployment
echo ============================================
echo.

REM ---- 1. Check Python 3 ----
echo [INFO] Checking for Python 3...
set "PYTHON="

python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
        for /f "tokens=1 delims=." %%m in ("%%v") do (
            if %%m GEQ 3 (
                set "PYTHON=python"
            )
        )
    )
)

if not defined PYTHON (
    python3 --version >nul 2>&1
    if %errorlevel%==0 (
        set "PYTHON=python3"
    )
)

if not defined PYTHON (
    echo [ERROR] Python 3 is required but not found.
    echo.
    echo   Download and install Python 3 from:
    echo     https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('%PYTHON% --version 2^>^&1') do echo [INFO] Found: %%v

REM ---- 2. Create virtual environment ----
if not exist "venv\" (
    echo [INFO] Creating virtual environment in .\venv ...
    %PYTHON% -m venv venv
) else (
    echo [INFO] Virtual environment already exists at .\venv
)

REM Activate
call venv\Scripts\activate.bat
echo [INFO] Virtual environment activated.

REM ---- 3. Install dependencies ----
echo [INFO] Installing Python dependencies...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo [INFO] Dependencies installed.

REM ---- 4. Generate SSL certificates (if missing) ----
if not exist "certs" mkdir certs

if not exist "certs\cert.pem" (
    if not exist "certs\key.pem" (
        echo [INFO] Checking for OpenSSL...
        where openssl >nul 2>&1
        if %errorlevel%==0 (
            echo [INFO] Generating self-signed SSL certificates...
            openssl req -x509 -newkey rsa:2048 -keyout certs\key.pem -out certs\cert.pem -days 365 -nodes -subj "/C=US/ST=Local/L=Local/O=Daycare/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>nul
            echo [INFO] SSL certificates generated in .\certs\
        ) else (
            echo [WARN] OpenSSL not found - skipping certificate generation.
            echo [WARN] The app will fall back to HTTP.
            echo [WARN] To enable HTTPS, install OpenSSL:
            echo         https://slproweb.com/products/Win32OpenSSL.html
            echo       Or install Git for Windows which includes OpenSSL.
        )
    )
) else (
    echo [INFO] SSL certificates already exist.
)

REM ---- 5. Initialize database ----
echo [INFO] Initializing database...
%PYTHON% -c "from database import init_db; init_db()"
echo [INFO] Database ready (daycare.db).

REM ---- 6. Seed admin user ----
echo [INFO] Checking for admin user...
for /f "tokens=*" %%a in ('%PYTHON% -c "from database import init_db, UserDB; _, s = init_db(); print('yes' if s.query(UserDB).filter_by(role='admin').first() else 'no'); s.close()"') do set "ADMIN_EXISTS=%%a"

if "%ADMIN_EXISTS%"=="no" (
    echo.
    echo ============================================
    echo   No admin user found. Creating one now.
    echo ============================================
    set "ADMIN_USER=admin"
    set "ADMIN_PASS=admin123"
    set /p "ADMIN_USER=  Admin username [admin]: "
    set /p "ADMIN_PASS=  Admin password [admin123]: "
    if "!ADMIN_USER!"=="" set "ADMIN_USER=admin"
    if "!ADMIN_PASS!"=="" set "ADMIN_PASS=admin123"
    %PYTHON% manage_users.py add-admin "!ADMIN_USER!" "!ADMIN_PASS!"
    echo [INFO] Admin user created.
) else (
    echo [INFO] Admin user already exists - skipping.
)

REM ---- 7. Create invoices directory ----
if not exist "invoices" mkdir invoices

REM ---- Done ----
echo.
echo ============================================
echo   Deployment complete!
echo ============================================
echo.
echo   To start the application:
echo.
echo     cd %~dp0
echo     venv\Scripts\activate.bat
echo     python app.py
echo.
echo   The app will be available at:
echo     https://localhost:5443
echo.
echo   Environment variables (optional):
echo     set SECRET_KEY=your-random-secret-key
echo     set PORT=5443
echo.
pause
