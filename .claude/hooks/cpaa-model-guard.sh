#!/usr/bin/env bash
# CPAA MODEL GUARD — Flags and blocks hardwired model names in code.
#
# MANDATE: All models must attach via env mount only.
# Code defines FUNCTION. Env defines PROVIDER/MODEL.
# Zero hardcoded model names in source code.
#
# Triggered on: PreToolUse (Write, Edit)
# Action: BLOCK if hardcoded model pattern detected

CONTENT="${TOOL_INPUT_CONTENT:-}${TOOL_INPUT_NEW_STRING:-}"

if [ -z "$CONTENT" ]; then
    exit 0
fi

FILE_PATH="${TOOL_INPUT_FILE_PATH:-}"

# Skip config/env files (these SHOULD have model names as defaults)
if echo "$FILE_PATH" | grep -qiE '(settings\.py|\.env|config\.py|model_router\.py|llm_provider\.py)'; then
    exit 0
fi

# Skip test files
if echo "$FILE_PATH" | grep -qiE '(test_|_test\.py|conftest\.py)'; then
    exit 0
fi

# Skip documentation
if echo "$FILE_PATH" | grep -qiE '\.(md|txt|rst|yml|yaml|json)$'; then
    exit 0
fi

VIOLATIONS=""

# Hardcoded Anthropic model names (should be from env)
if echo "$CONTENT" | grep -qE 'claude-opus-4|claude-sonnet-4|claude-haiku-4|claude-3-5|claude-3-opus|claude-3-haiku'; then
    # Check if it's in a string literal (not an import or comment)
    if echo "$CONTENT" | grep -qE '"claude-|'\''claude-|model.*=.*"claude|model.*=.*'\''claude'; then
        VIOLATIONS="${VIOLATIONS}\n- Hardcoded Claude model name detected. Use os.getenv('LLM_MODEL') or ModelRouter."
    fi
fi

# Hardcoded Bedrock model ARNs
if echo "$CONTENT" | grep -qE 'anthropic\.claude-|meta\.llama|cohere\.command'; then
    if echo "$CONTENT" | grep -qE '"anthropic\.|'\''anthropic\.|"meta\.|'\''meta\.|"cohere\.|'\''cohere\.'; then
        # Allow in model_router.py mapping table
        if ! echo "$FILE_PATH" | grep -q "model_router"; then
            VIOLATIONS="${VIOLATIONS}\n- Hardcoded Bedrock model ARN detected. Use ModelRouter.get_model() or env override."
        fi
    fi
fi

# Hardcoded OpenAI models
if echo "$CONTENT" | grep -qE '"gpt-4|'\''gpt-4|"gpt-3|'\''gpt-3|"o1-|'\''o1-'; then
    VIOLATIONS="${VIOLATIONS}\n- Hardcoded OpenAI model name detected. Use env-based model selection."
fi

# Hardcoded Gemini models
if echo "$CONTENT" | grep -qE '"gemini-|'\''gemini-'; then
    VIOLATIONS="${VIOLATIONS}\n- Hardcoded Gemini model name detected. Use env-based model selection."
fi

# Direct API client creation with hardcoded model
if echo "$CONTENT" | grep -qE 'model.*=.*"(claude|gpt|gemini|llama|cohere)'; then
    VIOLATIONS="${VIOLATIONS}\n- Direct model= assignment with hardcoded name. Use provider factory or env var."
fi

if [ -n "$VIOLATIONS" ]; then
    echo "CPAA MODEL GUARD VIOLATION"
    echo "=========================="
    echo "File: $FILE_PATH"
    echo ""
    echo "MANDATE: All models attach via env mount only."
    echo "Code = function. Env = provider/model."
    echo ""
    echo "Detected violations:"
    echo -e "$VIOLATIONS"
    echo ""
    echo "Fix: Use os.getenv('LLM_MODEL'), ModelRouter.get_model(), or MODEL_OVERRIDE_* env vars."
    echo "Exempt files: settings.py, model_router.py, llm_provider.py, tests, docs"
    exit 1
fi

exit 0
