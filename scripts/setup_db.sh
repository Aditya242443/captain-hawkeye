#!/usr/bin/env bash
# Project Plexis - Database Setup & Seeding Script

set -e

echo "=========================================="
echo "Project Plexis — Setting Up Supabase Database"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
else
    PYTHON_BIN="python"
fi

echo "Using Python: $PYTHON_BIN"
$PYTHON_BIN "$SCRIPT_DIR/seed_db.py"

echo "=========================================="
echo "Database Setup Complete!"
echo "=========================================="
