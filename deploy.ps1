# =============================================================================
# Daycare App — Windows PowerShell Deployment Script
# =============================================================================
# Run with: powershell -ExecutionPolicy Bypass -File deploy.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERROR] $args" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================"
Write-Host "  Daycare App - Windows Deployment"
Write-Host "============================================"
Write-Host ""

# ---- 1. Check Python 3 ----
Write-Info "Checking for Python 3..."
$Python = $null

foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") {
            $Python = $cmd
            break
        }
    } catch {}
}

if (-not $Python) {
    Write-Err "Python 3 is required but not found."
    Write-Host ""
    Write-Host "  Download and install Python 3 from:"
    Write-Host "    https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "  IMPORTANT: Check 'Add Python to PATH' during installation."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Info "Found: $(& $Python --version 2>&1)"

# ---- 2. Create virtual environment ----
$VenvDir = Join-Path $ScriptDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Info "Creating virtual environment in .\venv ..."
    & $Python -m venv $VenvDir
} else {
    Write-Info "Virtual environment already exists at .\venv"
}

# Activate
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    # Fallback: set PATH manually
    $env:PATH = (Join-Path $VenvDir "Scripts") + ";" + $env:PATH
    $env:VIRTUAL_ENV = $VenvDir
}
Write-Info "Virtual environment activated."

# ---- 3. Install dependencies ----
Write-Info "Installing Python dependencies..."
& pip install --upgrade pip --quiet 2>&1 | Out-Null
& pip install -r requirements.txt --quiet
Write-Info "Dependencies installed."

# ---- 4. Generate SSL certificates ----
$CertDir  = Join-Path $ScriptDir "certs"
$CertFile = Join-Path $CertDir "cert.pem"
$KeyFile  = Join-Path $CertDir "key.pem"

if (-not (Test-Path $CertDir)) { New-Item -ItemType Directory -Path $CertDir | Out-Null }

if (-not (Test-Path $CertFile) -or -not (Test-Path $KeyFile)) {
    Write-Info "Checking for OpenSSL..."
    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    if ($openssl) {
        Write-Info "Generating self-signed SSL certificates..."
        & openssl req -x509 -newkey rsa:2048 `
            -keyout $KeyFile -out $CertFile `
            -days 365 -nodes `
            -subj "/C=US/ST=Local/L=Local/O=Daycare/CN=localhost" `
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>&1 | Out-Null
        Write-Info "SSL certificates generated in .\certs\"
    } else {
        Write-Warn "OpenSSL not found - skipping certificate generation."
        Write-Warn "The app will fall back to HTTP."
        Write-Warn "To enable HTTPS, install OpenSSL or Git for Windows (includes OpenSSL)."
    }
} else {
    Write-Info "SSL certificates already exist."
}

# ---- 5. Initialize database ----
Write-Info "Initializing database..."
& $Python -c "from database import init_db; init_db()"
Write-Info "Database ready (daycare.db)."

# ---- 6. Seed admin user ----
Write-Info "Checking for admin user..."
$adminExists = & $Python -c "from database import init_db, UserDB; _, s = init_db(); print('yes' if s.query(UserDB).filter_by(role='admin').first() else 'no'); s.close()"

if ($adminExists.Trim() -eq "no") {
    Write-Host ""
    Write-Host "============================================"
    Write-Host "  No admin user found. Creating one now."
    Write-Host "============================================"
    $adminUser = Read-Host "  Admin username [admin]"
    if (-not $adminUser) { $adminUser = "admin" }
    $adminPass = Read-Host "  Admin password [admin123]"
    if (-not $adminPass) { $adminPass = "admin123" }
    & $Python manage_users.py add-admin $adminUser $adminPass
    Write-Info "Admin user '$adminUser' created."
} else {
    Write-Info "Admin user already exists - skipping."
}

# ---- 7. Create invoices directory ----
$InvDir = Join-Path $ScriptDir "invoices"
if (-not (Test-Path $InvDir)) { New-Item -ItemType Directory -Path $InvDir | Out-Null }

# ---- Done ----
Write-Host ""
Write-Host "============================================"
Write-Host "  Deployment complete!" -ForegroundColor Green
Write-Host "============================================"
Write-Host ""
Write-Host "  To start the application:"
Write-Host ""
Write-Host "    cd $ScriptDir"
Write-Host "    .\venv\Scripts\Activate.ps1"
Write-Host "    python app.py"
Write-Host ""
Write-Host "  The app will be available at:"
Write-Host "    https://localhost:5443"
Write-Host ""
Write-Host "  Environment variables (optional):"
Write-Host '    $env:SECRET_KEY = "your-random-secret-key"'
Write-Host '    $env:PORT = "5443"'
Write-Host ""
Read-Host "Press Enter to exit"
