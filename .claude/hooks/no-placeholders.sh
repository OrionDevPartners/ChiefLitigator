#!/usr/bin/env bash
# NO-PLACEHOLDERS HOOK — Hard Mandate
# Flags and blocks any placeholder, filler, simulation, or demo data
# in code being written to the Cyphergy repo.
#
# Triggered on: PreToolUse (Write, Edit)
# Action: BLOCK if placeholder patterns detected

FILE_PATH="${TOOL_INPUT_FILE_PATH:-}"
CONTENT="${TOOL_INPUT_CONTENT:-}"
NEW_STRING="${TOOL_INPUT_NEW_STRING:-}"

# Combine content sources
CHECK_CONTENT="${CONTENT}${NEW_STRING}"

if [ -z "$CHECK_CONTENT" ]; then
    exit 0
fi

# Patterns that indicate placeholder/filler/simulation/demo content
VIOLATIONS=""

# Check for common placeholder patterns
if echo "$CHECK_CONTENT" | grep -qiE 'TODO:.*implement|FIXME:.*placeholder|HACK:.*temporary'; then
    VIOLATIONS="${VIOLATIONS}\n- TODO/FIXME/HACK placeholder detected"
fi

if echo "$CHECK_CONTENT" | grep -qiE 'placeholder|lorem ipsum|dummy.data|fake.data|mock.data|sample.data'; then
    VIOLATIONS="${VIOLATIONS}\n- Placeholder/dummy/fake/mock/sample data pattern detected"
fi

if echo "$CHECK_CONTENT" | grep -qiE 'simulate|simulation|simulated|demo.mode|demo_mode|is_demo'; then
    VIOLATIONS="${VIOLATIONS}\n- Simulation/demo mode pattern detected"
fi

if echo "$CHECK_CONTENT" | grep -qiE 'return.*\[\].*#.*placeholder|return.*None.*#.*stub|pass.*#.*implement'; then
    VIOLATIONS="${VIOLATIONS}\n- Stub return with placeholder comment detected"
fi

if echo "$CHECK_CONTENT" | grep -qiE 'example\.com|test@test|user@example|john\.doe|jane\.doe'; then
    VIOLATIONS="${VIOLATIONS}\n- Fake email/domain pattern detected"
fi

if echo "$CHECK_CONTENT" | grep -qiE '"coming soon"|"not yet implemented"|"work in progress"'; then
    VIOLATIONS="${VIOLATIONS}\n- Filler text pattern detected"
fi

# Allow in test files and .env.example (these legitimately need placeholders)
if echo "$FILE_PATH" | grep -qE '(test_|_test\.py|\.env\.example|conftest\.py)'; then
    exit 0
fi

# Allow in documentation
if echo "$FILE_PATH" | grep -qiE '\.(md|txt|rst)$'; then
    exit 0
fi

if [ -n "$VIOLATIONS" ]; then
    echo "NO-PLACEHOLDERS MANDATE VIOLATION"
    echo "=================================="
    echo "File: $FILE_PATH"
    echo ""
    echo "Detected patterns:"
    echo -e "$VIOLATIONS"
    echo ""
    echo "HARD MANDATE: No placeholders, filler, simulations, or demo data."
    echo "Replace with actual working code before committing."
    echo ""
    echo "Exempt files: test_*, .env.example, *.md"
    exit 1
fi

exit 0
