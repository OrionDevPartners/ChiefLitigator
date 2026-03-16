# CYPHERGY — DEV TO PRODUCTION RUNBOOK
# Owner: Bo Pennington | bo@symio.ai
# Last Updated: 2026-03-16

---

## DEV ENVIRONMENT (M4 Max 48GB — Docker Desktop)

```bash
# === LLM ===
LLM_PROVIDER=anthropic                    # Direct Anthropic SDK
LLM_MODEL=claude-opus-4-6                 # Orchestrator + all agents
ANTHROPIC_API_KEY=sk-ant-xxx              # Your Anthropic key

# === Environment ===
APP_ENV=development
LOG_LEVEL=DEBUG

# === Database (local Docker) ===
DATABASE_URL=postgresql+asyncpg://cyphergy:cyphergy@localhost:5432/cyphergy

# === Redis (local Docker) ===
REDIS_URL=redis://localhost:6379/0

# === Auth (relaxed for dev) ===
JWT_SECRET_KEY=dev-secret-change-in-prod
ADMIN_JWT_SECRET=dev-admin-secret-change-in-prod
ADMIN_EMAIL=bo@symio.ai
REQUIRE_AUTH=false                         # No auth gate in dev
BETA_GATE_ENABLED=false                    # No IP lock in dev
IP_LOCK_ENABLED=false

# === CORS (local only) ===
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# === Feature Flags (all ON for testing) ===
DUAL_BRAIN_ENABLED=true                    # 3-model consensus
WDC_EXTENDED_PANEL=true                    # 8-model WDC
CRAWLER_ENABLED=false                      # Don't crawl in dev
HOLDING_EXTRACTION_ENABLED=true
ARGUMENT_GRAPH_ENABLED=true

# === External Services ===
COURTLISTENER_API_URL=https://www.courtlistener.com/api/rest/v4
COURTLISTENER_API_KEY=                     # Optional for dev

# === Monitoring (optional in dev) ===
SENTRY_DSN=                                # Set for error tracking
```

**Start dev:**
```bash
# Option 1: Just the API (quickest)
cd CIPHERGY-REPO
uvicorn src.api:app --reload --port 8000

# Option 2: Full stack (API + Postgres + Redis)
docker compose up

# Option 3: Just infrastructure (Postgres + Redis, API runs locally)
docker compose up postgres redis -d
uvicorn src.api:app --reload --port 8000
```

---

## STAGING ENVIRONMENT (ECS Fargate — pre-production)

```bash
# === LLM ===
LLM_PROVIDER=bedrock                       # AWS Bedrock
LLM_MODEL=claude-opus-4-6                  # Maps to anthropic.claude-opus-4-6-v1
AWS_DEFAULT_REGION=us-east-1

# === Environment ===
APP_ENV=staging
LOG_LEVEL=INFO

# === Database (RDS) ===
DATABASE_URL=postgresql+asyncpg://cyphergy_admin:PASSWORD@cyphergy-beta.cgf2g0i0o0zu.us-east-1.rds.amazonaws.com:5432/cyphergy

# === Redis (ElastiCache) ===
REDIS_URL=redis://cyphergy-redis.xxx.use1.cache.amazonaws.com:6379/0

# === Auth (enforced) ===
JWT_SECRET_KEY=<generated-hex-32>
ADMIN_JWT_SECRET=<different-generated-hex-32>
ADMIN_EMAIL=bo@symio.ai
REQUIRE_AUTH=true
BETA_GATE_ENABLED=true
IP_LOCK_ENABLED=true

# === CORS (staging domains) ===
CORS_ALLOWED_ORIGINS=https://staging.cyphergy.ai,https://admin-staging.cyphergy.ai

# === Feature Flags (selective — enable one at a time) ===
DUAL_BRAIN_ENABLED=false                   # Enable after single-agent verified
WDC_EXTENDED_PANEL=false                   # Enable after base WDC verified
CRAWLER_ENABLED=false                      # Enable after DB verified
HOLDING_EXTRACTION_ENABLED=false
ARGUMENT_GRAPH_ENABLED=false

# === Monitoring (required) ===
SENTRY_DSN=https://xxx@sentry.io/yyy
```

---

## PRODUCTION ENVIRONMENT (ECS Fargate — live users)

```bash
# === LLM ===
LLM_PROVIDER=bedrock
LLM_MODEL=claude-opus-4-6
AWS_DEFAULT_REGION=us-east-1

# === Environment ===
APP_ENV=production
LOG_LEVEL=INFO

# === Database (RDS) ===
DATABASE_URL=postgresql+asyncpg://cyphergy_admin:PASSWORD@cyphergy-beta.cgf2g0i0o0zu.us-east-1.rds.amazonaws.com:5432/cyphergy

# === Redis ===
REDIS_URL=redis://cyphergy-redis.xxx.use1.cache.amazonaws.com:6379/0

# === Auth (fully enforced) ===
JWT_SECRET_KEY=<production-hex-32>
ADMIN_JWT_SECRET=<production-admin-hex-32>
ADMIN_EMAIL=bo@symio.ai
REQUIRE_AUTH=true
BETA_GATE_ENABLED=true
IP_LOCK_ENABLED=true

# === CORS (production domains only) ===
CORS_ALLOWED_ORIGINS=https://cyphergy.ai,https://admin.cyphergy.ai

# === Feature Flags (progressive enable) ===
DUAL_BRAIN_ENABLED=true                    # After staging verified
WDC_EXTENDED_PANEL=true                    # After staging verified
CRAWLER_ENABLED=true                       # Perpetual background task
HOLDING_EXTRACTION_ENABLED=true
ARGUMENT_GRAPH_ENABLED=true

# === Monitoring (required) ===
SENTRY_DSN=https://xxx@sentry.io/yyy

# === Model Overrides (auto-rotation) ===
# MODEL_OVERRIDE_ORCHESTRATOR=anthropic.claude-opus-4-7-v1  # When 4.7 releases
# MODEL_OVERRIDE_JURISDICTION_SCOUT=meta.llama5-scout-v1:0  # When Llama 5 releases
```

---

## DEPLOYMENT PROTOCOL

### Triggers

```
Push to dev                    → CI: lint + security + tests
dev → staging PR               → WDC gate (score >= 7.5 required)
staging → main PR              → WDC gate + manual approval
Push to main                   → Auto build → ECR push → ECS deploy

Devin PR to any branch         → WDC gate blocks without approval
Any file deletion in PR        → Deletion guard blocks protected paths
```

### Flow

```
DEV (local Mac)
  │
  ├── uvicorn --reload (fast iteration)
  ├── docker compose up (full stack test)
  └── pytest (33+ tests must pass)
  │
  ▼
FEATURE BRANCH
  │
  ├── git push origin feature/xxx
  ├── CI runs: lint, security scan, tests
  └── PR created → dev
  │
  ▼
DEV BRANCH (Devin merges freely here)
  │
  ├── All PRs get auto-review comment
  ├── Tests must pass
  └── Ready for staging promotion
  │
  ▼
STAGING BRANCH (WDC gated)
  │
  ├── PR from dev → staging
  ├── WDC merge gate: COMPOSITE SCORE >= 7.5 required
  ├── 1 approving review required
  ├── CI must pass
  └── Feature flags: OFF by default, enable one at a time
  │
  ▼
MAIN BRANCH (production — manual approval)
  │
  ├── PR from staging → main ONLY
  ├── WDC merge gate: COMPOSITE SCORE >= 7.5
  ├── 1 approving review + admin enforcement
  ├── CI must pass
  └── Auto-deploy on merge:
      │
      ├── GitHub Actions builds Docker image
      ├── Pushes to ECR (222257058350.dkr.ecr.us-east-1.amazonaws.com/cyphergy-api)
      ├── Updates ECS task definition
      ├── ECS Fargate pulls new image
      ├── Alembic migration runs (init container)
      ├── Health check passes (/health returns 200)
      └── LIVE on cyphergy.ai
```

---

## HOOKS

### Claude Code Hooks (.claude/settings.json)

```
UserPromptSubmit:
  - memory-inject.sh          Load MEMORY.md at session start
  - context-guard.sh          Keep focus on current task from TODO.md

PreToolUse (Write|Edit):
  - memory-guard.sh            Warn on memory writes outside canonical paths
  - no-placeholders.sh         Block fake/demo/placeholder data (24 patterns)

PostToolUse (Write|Edit):
  - post-edit-logger.sh        Log all file changes
```

### GitHub Workflows (.github/workflows/)

```
ci.yml:
  Trigger: push + PR to any branch
  Jobs: lint (ruff), typecheck (mypy), test (pytest matrix 3.11/3.12),
        security (bandit + pip-audit), secrets-scan (gitleaks)
  Rule: ALL gates enforced — no continue-on-error

security-scan.yml:
  Trigger: weekly (Monday 06:00 UTC) + manual
  Jobs: dependency-audit, SAST, secrets-scan, OWASP dependency-check

wdc-gate.yml:
  Trigger: PR to dev/staging/main + PR comments
  Jobs:
    dev → informational only (auto-review comment, no block)
    staging → BLOCKS: WDC score >= 7.5 + 1 approval
    main → BLOCKS: WDC score >= 7.5 + 1 approval + staging source only
  Protection: deletion guard on DOCS/, MEMORY.md, GUARDRAILS.yml,
              citation_chain.py, deadline_calc.py, wdc.py, settings.py
```

### Git Branch Protection (enforced via GitHub API)

```
staging:
  - Required checks: "WDC Gate (staging)", "Deletion Protection"
  - 1 approving review
  - Enforce admins: true
  - Force push: blocked
  - Deletions: blocked

main:
  - Required checks: "WDC Gate (main — production)", "Deletion Protection"
  - 1 approving review
  - Enforce admins: true
  - Force push: blocked
  - Deletions: blocked
  - Only staging can merge to main
```

---

## SECURITY GATES

| Gate | Where | What It Blocks |
|------|-------|---------------|
| LLM Guardrails | Orchestrator | Jailbreaks, model identity leaks, architecture leaks |
| No-Placeholders Hook | Claude Code | Fake data, demo content, placeholder text |
| WDC Merge Gate | GitHub Actions | PRs without WDC score >= 7.5 |
| Deletion Guard | GitHub Actions | Protected file deletions |
| Beta Gate | API Middleware | Non-invited users, wrong IP |
| Rate Limiter | API Middleware | 4-layer: IP → user → tenant → global |
| Source Protection | Cloudflare WAF | Source maps, webpack artifacts |
| JWT Auth | API Middleware | Unsigned/expired tokens |
| Admin Auth | API Middleware | Non-admin access to /admin/* |
| Bandit | CI Pipeline | Code-level security vulnerabilities |
| Gitleaks | CI Pipeline | Accidentally committed secrets |

---

## HEALTH CHECKS

```
GET /health           → {"status": "ok", "agents": 5, "tests_passing": 33}
GET /health/ready     → {"ready": true, "provider": "bedrock"}
```

ECS health check: `curl -f http://localhost:8000/health || exit 1` (30s interval, 5s timeout, 3 retries)

---

## EMERGENCY PROCEDURES

```
ROLLBACK:
  aws ecs update-service --cluster cyphergy --service cyphergy-api \
    --task-definition cyphergy-api:PREVIOUS_REVISION --force-new-deployment

CIRCUIT BREAKER:
  Rate limiter auto-trips at 5000 req/min global → returns 503
  Manual reset via admin panel or restart

KILL SWITCH:
  Set APP_ENV=maintenance in ECS task def → returns 503 to all requests
```

---

*Cyphergy Runbook v1.0 — Dev to Production*
