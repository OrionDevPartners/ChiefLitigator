#!/bin/bash
# CIPHERGY — Session Startup Hook
# Fires automatically on every new Claude Code session
set -e
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══════════════════════════════════════════════════"
echo "  CIPHERGY — SESSION STARTUP"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════"
echo ""
python3 "$BASE/scripts/nerve_center.py" startup 2>&1 || echo "[WARN] nerve_center failed"
echo ""
# Read agent comms if configured
if python3 "$BASE/scripts/agent_comm.py" status 2>/dev/null | grep -q "Last msg"; then
    python3 "$BASE/scripts/agent_comm.py" read 2>&1 || echo "[WARN] agent_comm failed"
fi
echo "═══════════════════════════════════════════════════"
echo "  STARTUP COMPLETE"
echo "═══════════════════════════════════════════════════"
exit 0
