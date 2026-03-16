#!/usr/bin/env bash
# ENV GUARD — Ensures dev and production environments never cross-contaminate.
#
# DEV:  n8n, Docker Postgres, Docker Redis, Anthropic or Bedrock
# PROD: AWS Step Functions, RDS Aurora, ElastiCache, Bedrock only
#
# This hook runs on PreToolUse (Write/Edit) and warns if production
# config is being written into dev files or vice versa.

FILE_PATH="${TOOL_INPUT_FILE_PATH:-}"
CONTENT="${TOOL_INPUT_CONTENT:-}${TOOL_INPUT_NEW_STRING:-}"

if [ -z "$CONTENT" ] || [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Skip non-config files
if ! echo "$FILE_PATH" | grep -qiE '(\.env|docker-compose|settings|config|deploy)'; then
    exit 0
fi

VIOLATIONS=""

# Don't put production RDS URLs in dev config
if echo "$FILE_PATH" | grep -qiE '\.env\.development|docker-compose\.dev'; then
    if echo "$CONTENT" | grep -qE '\.rds\.amazonaws\.com|elasticache|\.cache\.amazonaws'; then
        VIOLATIONS="${VIOLATIONS}\n- Production database/cache URL in dev config. Use localhost for dev."
    fi
fi

# Don't put localhost in production config
if echo "$FILE_PATH" | grep -qiE '\.env\.production|deploy-production|ecs-task'; then
    if echo "$CONTENT" | grep -qE 'localhost|127\.0\.0\.1|0\.0\.0\.0'; then
        VIOLATIONS="${VIOLATIONS}\n- Localhost URL in production config. Use AWS service endpoints."
    fi
fi

# Don't disable security in production
if echo "$FILE_PATH" | grep -qiE '\.env\.production'; then
    if echo "$CONTENT" | grep -qiE 'DEBUG=true|BETA_GATE_ENABLED=false|RATE_LIMIT_ENABLED=false'; then
        VIOLATIONS="${VIOLATIONS}\n- Security disabled in production config. Keep DEBUG=false, gates ON."
    fi
fi

if [ -n "$VIOLATIONS" ]; then
    echo "ENV GUARD WARNING"
    echo "================="
    echo "File: $FILE_PATH"
    echo ""
    echo "Dev and production environments must stay separate:"
    echo "  DEV:  localhost, n8n, Docker Postgres/Redis"
    echo "  PROD: AWS RDS, ElastiCache, Step Functions, Bedrock"
    echo ""
    echo "Detected issues:"
    echo -e "$VIOLATIONS"
    # Warning only — don't block (some files legitimately reference both)
    exit 0
fi

exit 0
