#!/bin/bash
# CIPHERGY — Post-Edit Logger Hook
# Fires after every Edit/Write tool call
set -e
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"' 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0
[[ "$FILE_PATH" == *"/DIFF/"* ]] && exit 0
mkdir -p "$BASE/DIFF"
DIFF_FILE="$BASE/DIFF/$(date '+%Y-%m-%d')_auto_diffs.md"
[ ! -f "$DIFF_FILE" ] && echo "# AUTO DIFF LOG — $(date '+%Y-%m-%d')" > "$DIFF_FILE"
echo "- \`$(date '+%Y-%m-%d %H:%M:%S')\` | **$TOOL_NAME** | \`$FILE_PATH\`" >> "$DIFF_FILE"
exit 0
