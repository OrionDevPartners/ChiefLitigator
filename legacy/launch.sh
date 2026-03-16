#!/bin/bash
# CIPHERGY COMMAND CENTER — Launcher
# Runs locally on 127.0.0.1:5000

echo "═══════════════════════════════════════"
echo "  CIPHERGY COMMAND CENTER"
echo "  http://127.0.0.1:5000"
echo "  Press Ctrl+C to stop"
echo "═══════════════════════════════════════"

cd "$(dirname "$0")"

# Set case directory if not set
export CIPHERGY_CASE_DIR="${CIPHERGY_CASE_DIR:-/Users/bopennington/LEGAL 2026 Pro Se/CAMPENNI_CASE}"

# Launch Flask
python3 ciphergy/command_center/app.py
