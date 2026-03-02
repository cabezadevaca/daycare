# Daycare App — Deployment Guide

## Prerequisites

- **Python 3.6+** (3.8+ recommended) — auto-installed by the deploy scripts if not found
- **OpenSSL** (optional, for HTTPS — the app falls back to HTTP if certs are missing)

---

## Quick Deploy

### Linux

```bash
chmod +x deploy.sh start.sh
./deploy.sh
./start.sh
```

> Python 3 will be auto-installed via `apt`, `dnf`, `pacman`, or `zypper` if not found.

### macOS

```bash
chmod +x deploy-mac.sh start.sh
./deploy-mac.sh
./start.sh
```

> Homebrew and Python 3 will be auto-installed if not found.

### Windows (Command Prompt)

```cmd
deploy.bat
start.bat
```

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File deploy.ps1
.\venv\Scripts\Activate.ps1
python app.py
```

---

## What the Deploy Scripts Do

1. **Check Python 3** — verifies `python3` or `python` is available
2. **Create virtual environment** — in `./venv`
3. **Install dependencies** — from `requirements.txt`
4. **Generate SSL certificates** — self-signed certs in `./certs/` (requires OpenSSL)
5. **Initialize database** — creates `daycare.db` with all tables
6. **Seed admin user** — prompts for username/password if no admin exists
7. **Create invoices directory** — for generated PDF invoices

---

## Copying to Another Computer

Copy the **entire project folder** to the target machine. You have two options:

### Option A: Fresh deploy (recommended)

Copy everything **except** `venv/`, `__pycache__/`, and `*.pyc`:

```
daycare/
├── app.py
├── actors.py
├── database.py
├── daycare.py
├── emailpdf.py
├── invoice.py
├── timetable.py
├── manage_users.py
├── migrate_to_sqlite.py
├── requirements.txt
├── deploy.sh / deploy-mac.sh / deploy.bat / deploy.ps1
├── start.sh / start.bat
├── certs/              (optional — will be regenerated)
├── static/
├── templates/
├── daycare.db          (include to keep existing data)
└── invoices/           (include to keep generated PDFs)
```

Then run `deploy.sh` (Linux), `deploy-mac.sh` (macOS), or `deploy.bat` (Windows).

### Option B: Copy with existing data

Include `daycare.db` and the `invoices/` folder to preserve all families, invoices, and user accounts.

---

## Environment Variables

| Variable     | Default                            | Description                    |
|--------------|------------------------------------|--------------------------------|
| `SECRET_KEY` | `change-me-to-a-random-secret-key` | Flask session encryption key   |
| `PORT`       | `5443`                             | Server port                    |

**Linux/macOS:**
```bash
export SECRET_KEY="my-super-secret-key"
export PORT=8443
```

**Windows (CMD):**
```cmd
set SECRET_KEY=my-super-secret-key
set PORT=8443
```

**Windows (PowerShell):**
```powershell
$env:SECRET_KEY = "my-super-secret-key"
$env:PORT = "8443"
```

---

## Managing Users

```bash
# Add admin
python manage_users.py add-admin <username> <password>

# Add parent (linked to a family)
python manage_users.py add-parent <username> <password> <family_id>

# List all users
python manage_users.py list

# Delete a user
python manage_users.py delete <username>
```

---

## Troubleshooting

- **"Python not found"** — Install Python 3 and ensure it's on your PATH
- **"SSL certificates not found"** — Install OpenSSL, or the app will use HTTP instead
- **Port already in use** — Set a different port: `export PORT=8444` (or `set PORT=8444` on Windows)
- **Database issues** — Delete `daycare.db` and re-run the deploy script for a fresh start
