#!/usr/bin/env bash
# Quick-start script for Linux/macOS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run deploy.sh first."
    exit 1
fi

source venv/bin/activate
echo "Starting Daycare App..."
python app.py
