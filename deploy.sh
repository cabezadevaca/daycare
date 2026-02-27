#!/usr/bin/env bash
# =============================================================================
# Daycare App — Linux/macOS Deployment Script
# =============================================================================
# This script:
#   1. Checks for Python 3
#   2. Creates a virtual environment
#   3. Installs dependencies
#   4. Generates self-signed SSL certificates (if missing)
#   5. Initializes the database (tables are auto-created on first run)
#   6. Seeds an admin user (if none exists)
#   7. Prints instructions to start the app
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---- 1. Check Python 3 ----
info "Checking for Python 3..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        if [ "$major" -ge 3 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3 is required but not found."
    echo "  Install it with your package manager, e.g.:"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "    Fedora:        sudo dnf install python3"
    echo "    macOS:         brew install python3"
    exit 1
fi
info "Found Python: $($PYTHON --version)"

# ---- 2. Create virtual environment ----
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment in ./venv ..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    info "Virtual environment already exists at ./venv"
fi

# Activate
source "$VENV_DIR/bin/activate"
info "Virtual environment activated."

# ---- 3. Install dependencies ----
info "Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
info "Dependencies installed."

# ---- 4. Generate SSL certificates (if missing) ----
CERT_DIR="$SCRIPT_DIR/certs"
CERTFILE="$CERT_DIR/cert.pem"
KEYFILE="$CERT_DIR/key.pem"

if [ ! -f "$CERTFILE" ] || [ ! -f "$KEYFILE" ]; then
    info "Generating self-signed SSL certificates..."
    mkdir -p "$CERT_DIR"
    if command -v openssl &>/dev/null; then
        openssl req -x509 -newkey rsa:2048 \
            -keyout "$KEYFILE" -out "$CERTFILE" \
            -days 365 -nodes \
            -subj "/C=US/ST=Local/L=Local/O=Daycare/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
        info "SSL certificates generated in ./certs/"
    else
        warn "openssl not found — skipping certificate generation."
        warn "The app will fall back to HTTP. Install openssl to enable HTTPS."
    fi
else
    info "SSL certificates already exist."
fi

# ---- 5. Initialize database ----
info "Initializing database (creating tables if needed)..."
"$PYTHON" -c "from database import init_db; init_db()"
info "Database ready (daycare.db)."

# ---- 6. Seed admin user ----
info "Checking for admin user..."
ADMIN_EXISTS=$("$PYTHON" -c "
from database import init_db, UserDB
_, session = init_db()
admin = session.query(UserDB).filter_by(role='admin').first()
print('yes' if admin else 'no')
session.close()
")

if [ "$ADMIN_EXISTS" = "no" ]; then
    echo ""
    echo "============================================"
    echo "  No admin user found. Creating one now."
    echo "============================================"
    read -rp "  Admin username [admin]: " ADMIN_USER
    ADMIN_USER="${ADMIN_USER:-admin}"
    read -rsp "  Admin password [admin123]: " ADMIN_PASS
    echo ""
    ADMIN_PASS="${ADMIN_PASS:-admin123}"
    "$PYTHON" manage_users.py add-admin "$ADMIN_USER" "$ADMIN_PASS"
    info "Admin user '$ADMIN_USER' created."
else
    info "Admin user already exists — skipping."
fi

# ---- 7. Create invoices directory ----
mkdir -p "$SCRIPT_DIR/invoices"

# ---- Done ----
echo ""
echo "============================================"
echo -e "  ${GREEN}Deployment complete!${NC}"
echo "============================================"
echo ""
echo "  To start the application:"
echo ""
echo "    cd $SCRIPT_DIR"
echo "    source venv/bin/activate"
echo "    python app.py"
echo ""
echo "  The app will be available at:"
echo "    https://localhost:5443"
echo ""
echo "  You can also set these environment variables:"
echo "    SECRET_KEY   — Flask session secret (recommended for production)"
echo "    PORT         — Server port (default: 5443)"
echo ""
echo "  Quick start (run now):"
echo "    source venv/bin/activate && python app.py"
echo ""
