# CYPHERGY — DEVELOPMENT TO PRODUCTION PROTOCOL

## Environment Strategy, Test Gates, Deployment Triggers & Git Hooks

**Version 2.0 — March 2026**

---

## TABLE OF CONTENTS

1. Three-Environment Architecture
2. Development Environment (.env.development)
3. Staging Environment (.env.staging)
4. Production Environment (.env.production)
5. The Promotion Protocol (Dev -> Staging -> Prod)
6. Test Gates (What Must Pass Before Promotion)
7. Git Hooks (Automated Quality Gates)
8. Claude Code Hooks (WDC Integration)
9. GitHub Actions Triggers
10. Admin Panel Deployment
11. Background Services (Perpetual Crawler)
12. Feature Flag Progressive Rollout
13. Emergency Rollback Protocol

---

## 1. THREE-ENVIRONMENT ARCHITECTURE

```
+---------------------------------------------------------------------------+
|                     DEVELOPMENT (Mac Docker Desktop)                       |
|                                                                            |
|  Docker Desktop                                                            |
|  +-- api container (FastAPI on :8000)                                      |
|  +-- db container (pgvector/pgvector:pg16 on :5432)                        |
|  +-- redis container (rate limiting + cache)                               |
|                                                                            |
|  Frontend: npm run dev -> localhost:3000 -> proxies /api to :8000          |
|  Secrets: .env.development (local file, never committed)                   |
|  LLM: Anthropic SDK (direct API calls) OR mock mode (fast iteration)       |
|  Logs: Terminal stdout (instant)                                           |
|  Tests: pytest locally, pre-commit hooks enforce                           |
|  Branch: feature/* or dev                                                  |
|  Gate: Devin merges freely to dev -- no WDC gate                           |
+------------------------------------+--------------------------------------+
                                     |
                              All tests pass?
                              CI green?
                              PR approved?
                                     |
                                     v
+---------------------------------------------------------------------------+
|                     STAGING (AWS ECS Fargate)                               |
|                                                                            |
|  AWS ECS Fargate (backend)                                                 |
|  +-- ECR (container registry)                                              |
|  +-- Secrets Manager (all credentials)                                     |
|  +-- CloudWatch (logs)                                                     |
|  +-- S3 (case files, encrypted)                                            |
|  RDS PostgreSQL (database)                                                 |
|  Sentry (error tracking, PII scrubbed)                                     |
|                                                                            |
|  Feature Flags: ALL OFF (test baseline)                                    |
|  Beta Gate: ENABLED (invite-only, IP-locked)                               |
|  Branch: staging (WDC score >= 7.5 + 1 approval required)                 |
+------------------------------------+--------------------------------------+
                                     |
                              WDC score 7.5+?
                              Manual approval?
                              All flags tested?
                              Only from staging?
                                     |
                                     v
+---------------------------------------------------------------------------+
|                     PRODUCTION (AWS ECS Fargate)                            |
|                                                                            |
|  Cloudflare Pages (frontend: cyphergy.ai)                                  |
|  Cloudflare Pages (admin: admin.cyphergy.ai -- SEPARATE project)           |
|  AWS ECS Fargate (backend API)                                             |
|  +-- ECR (container registry)                                              |
|  +-- Secrets Manager (all credentials)                                     |
|  +-- CloudWatch (logs)                                                     |
|  +-- S3 (case files, encrypted)                                            |
|  RDS PostgreSQL (database) -> Aurora (scale path)                          |
|  Sentry (error tracking, PII scrubbed)                                     |
|                                                                            |
|  Feature Flags: Progressive enable via admin panel                         |
|  Beta Gate: ENABLED (invite-only, IP-locked)                               |
|  Crawler: Separate Fargate task (perpetual)                                |
|  Branch: main (only merged from staging, manual approval)                  |
+---------------------------------------------------------------------------+
```

---

## 2. DEVELOPMENT ENVIRONMENT

### File: `.env.development`

```bash
# ============================================
# CYPHERGY -- DEVELOPMENT ENVIRONMENT
# Location: Project root (NEVER committed)
# Usage: docker compose --env-file .env.development up --build
# ============================================

# === ENVIRONMENT FLAG ===
ENVIRONMENT=development
APP_ENV=development
DEBUG=true
LOG_LEVEL=debug
APP_PORT=8000

# === DATABASE (Local Docker pgvector) ===
DATABASE_URL=postgresql+asyncpg://cyphergy:localdev@db:5432/cyphergy
DATABASE_POOL_SIZE=5
DATABASE_ECHO=true

# === LLM (Anthropic SDK -- direct API in dev) ===
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-4-6
ANTHROPIC_API_KEY=sk-ant-xxx

# === MOCK MODE (Uncomment to skip real LLM calls during dev) ===
# LLM_MOCK_MODE=true
# LLM_MOCK_RESPONSE="This is a mock agent response for development."

# === AUTH (Dev keys -- NOT production values) ===
JWT_SECRET_KEY=dev-only-jwt-secret-do-not-use-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
ADMIN_JWT_SECRET=dev-admin-secret-do-not-use-in-production
ADMIN_EMAIL=bo@symio.ai
REQUIRE_AUTH=false

# === BETA GATE (Disabled in dev) ===
BETA_GATE_ENABLED=false
IP_LOCK_ENABLED=false

# === CORS (Allow local frontend) ===
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173,http://127.0.0.1:5173

# === RATE LIMITING (Relaxed for dev) ===
RATE_LIMIT_ENABLED=false

# === SENTRY (Disabled in dev -- no noise) ===
SENTRY_DSN=
SENTRY_ENABLED=false

# === REDIS (Local Docker) ===
REDIS_URL=redis://redis:6379/0

# === FILE STORAGE (Local volume, not S3) ===
FILE_STORAGE_PROVIDER=local
LOCAL_CASE_FILES_PATH=./case_files

# === EXTERNAL SERVICES ===
COURTLISTENER_API_URL=https://www.courtlistener.com/api/rest/v4
COURTLISTENER_API_KEY=

# === CONNECTORS (Optional -- only enable what you're testing) ===
# GMAIL_CREDENTIALS=
# GOOGLE_DRIVE_CREDENTIALS=
# GOOGLE_CALENDAR_CREDENTIALS=
# ASANA_TOKEN=
# SLACK_BOT_TOKEN=
# NOTION_TOKEN=

# === FEATURE FLAGS (All ON for testing in dev) ===
DUAL_BRAIN_ENABLED=true
WDC_EXTENDED_PANEL=true
CRAWLER_ENABLED=false
HOLDING_EXTRACTION_ENABLED=true
ARGUMENT_GRAPH_ENABLED=true
```

### Docker Compose for Development: `docker-compose.dev.yml`

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: .env.development
    volumes:
      - ./src:/app/src          # Hot reload -- edit code, container sees it
      - ./tests:/app/tests
      - ./config:/app/config
      - ./prompts:/app/prompts
      - ./case_files:/app/case_files
    command: uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: cyphergy
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: cyphergy
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cyphergy"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

### Dev Commands

```bash
# Start everything
docker compose -f docker-compose.dev.yml --env-file .env.development up --build

# Run tests inside the container
docker compose -f docker-compose.dev.yml exec api pytest tests/ -v

# Reset database
docker compose -f docker-compose.dev.yml exec db psql -U cyphergy -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# View logs (already in terminal, but if backgrounded)
docker compose -f docker-compose.dev.yml logs -f api

# Stop everything
docker compose -f docker-compose.dev.yml down

# Nuclear reset (wipe volumes)
docker compose -f docker-compose.dev.yml down -v

# Quick start (no Docker -- local only)
uvicorn src.api:app --reload --port 8000
```

---

## 3. STAGING ENVIRONMENT

### File: `.env.staging` (Reference only -- actual values in AWS Secrets Manager)

```bash
# ============================================
# CYPHERGY -- STAGING ENVIRONMENT
# THIS FILE IS A REFERENCE. DO NOT DEPLOY FROM IT.
# All values are injected via AWS Secrets Manager -> ECS task definition.
# ============================================

# === ENVIRONMENT FLAG ===
ENVIRONMENT=staging
APP_ENV=staging
DEBUG=false
LOG_LEVEL=info
APP_PORT=8000

# === DATABASE (RDS PostgreSQL) ===
DATABASE_URL=postgresql+asyncpg://cyphergy_admin:PASSWORD@cyphergy-beta.cgf2g0i0o0zu.us-east-1.rds.amazonaws.com:5432/cyphergy
DATABASE_POOL_SIZE=10
DATABASE_ECHO=false

# === LLM (AWS Bedrock) ===
# No keys needed -- Fargate task role has bedrock:InvokeModel permission
LLM_PROVIDER=bedrock
LLM_MODEL=claude-opus-4-6
AWS_DEFAULT_REGION=us-east-1
BEDROCK_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=anthropic.claude-opus-4-6-v1
BEDROCK_HEAVY_MODEL=anthropic.claude-opus-4-6-v1
BEDROCK_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0
BEDROCK_SCOUT_MODEL=meta.llama4-scout-17b-instruct-v1:0
BEDROCK_COHERE_MODEL=cohere.command-r-plus-v1:0

# === MOCK MODE ===
LLM_MOCK_MODE=false

# === AUTH (Enforced) ===
JWT_SECRET_KEY=<injected-from-secrets-manager>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
ADMIN_JWT_SECRET=<injected-from-secrets-manager-different-key>
ADMIN_EMAIL=bo@symio.ai
REQUIRE_AUTH=true

# === BETA GATE (Enforced) ===
BETA_GATE_ENABLED=true
IP_LOCK_ENABLED=true

# === CORS (Staging domains) ===
CORS_ORIGINS=https://staging.cyphergy.ai,https://admin-staging.cyphergy.ai

# === RATE LIMITING (Enforced) ===
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_BURST=10

# === REDIS (ElastiCache) ===
REDIS_URL=redis://cyphergy-redis.xxx.use1.cache.amazonaws.com:6379/0

# === SENTRY (Live, PII scrubbing active) ===
SENTRY_DSN=<injected-from-secrets-manager>
SENTRY_ENABLED=true
SENTRY_TRACES_SAMPLE_RATE=0.2

# === FILE STORAGE (S3, encrypted) ===
FILE_STORAGE_PROVIDER=s3
S3_CASE_FILES_BUCKET=cyphergy-documents-staging
S3_REGION=us-east-1

# === EXTERNAL SERVICES ===
COURTLISTENER_API_URL=https://www.courtlistener.com/api/rest/v4
COURTLISTENER_API_KEY=<injected-from-secrets-manager>

# === FEATURE FLAGS (ALL OFF -- test baseline) ===
DUAL_BRAIN_ENABLED=false
WDC_EXTENDED_PANEL=false
CRAWLER_ENABLED=false
HOLDING_EXTRACTION_ENABLED=false
ARGUMENT_GRAPH_ENABLED=false

# === CLOUDFLARE ===
CLOUDFLARE_ACCOUNT_ID=<in-github-secrets>
CLOUDFLARE_API_TOKEN=<in-github-secrets>
```

---

## 4. PRODUCTION ENVIRONMENT

### File: `.env.production` (Reference only -- actual values in AWS Secrets Manager)

```bash
# ============================================
# CYPHERGY -- PRODUCTION ENVIRONMENT
# THIS FILE IS A REFERENCE. DO NOT DEPLOY FROM IT.
# All values are injected via AWS Secrets Manager -> ECS task definition.
# ============================================

# === ENVIRONMENT FLAG ===
ENVIRONMENT=production
APP_ENV=production
DEBUG=false
LOG_LEVEL=info
APP_PORT=8000

# === DATABASE (RDS PostgreSQL) ===
# Injected from: arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:cyphergy/production/database
DATABASE_URL=postgresql+asyncpg://cyphergy_admin:PASSWORD@cyphergy-prod.cgf2g0i0o0zu.us-east-1.rds.amazonaws.com:5432/cyphergy
DATABASE_POOL_SIZE=20
DATABASE_ECHO=false

# === LLM (AWS Bedrock) ===
# No keys needed -- Fargate task role has bedrock:InvokeModel permission
LLM_PROVIDER=bedrock
LLM_MODEL=claude-opus-4-6
AWS_DEFAULT_REGION=us-east-1
BEDROCK_REGION=us-east-1
BEDROCK_DEFAULT_MODEL=anthropic.claude-opus-4-6-v1
BEDROCK_HEAVY_MODEL=anthropic.claude-opus-4-6-v1
BEDROCK_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0
BEDROCK_SCOUT_MODEL=meta.llama4-scout-17b-instruct-v1:0
BEDROCK_COHERE_MODEL=cohere.command-r-plus-v1:0

# === MOCK MODE ===
LLM_MOCK_MODE=false

# === AUTH (Fully enforced) ===
# Injected from: arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:cyphergy/production/auth
JWT_SECRET_KEY=<injected-from-secrets-manager>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
ADMIN_JWT_SECRET=<injected-from-secrets-manager-different-key>
ADMIN_EMAIL=bo@symio.ai
REQUIRE_AUTH=true

# === BETA GATE (Enforced -- invite-only access) ===
BETA_GATE_ENABLED=true
IP_LOCK_ENABLED=true

# === CORS (Production domains only) ===
CORS_ORIGINS=https://cyphergy.ai,https://www.cyphergy.ai,https://admin.cyphergy.ai,https://cyphergy.pages.dev

# === RATE LIMITING (Enforced) ===
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_BURST=10

# === REDIS (ElastiCache) ===
REDIS_URL=redis://cyphergy-redis.xxx.use1.cache.amazonaws.com:6379/0

# === SENTRY (Live, PII scrubbing active) ===
# Injected from: arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:cyphergy/production/sentry
SENTRY_DSN=<injected-from-secrets-manager>
SENTRY_ENABLED=true
SENTRY_TRACES_SAMPLE_RATE=0.1

# === FILE STORAGE (S3, encrypted) ===
FILE_STORAGE_PROVIDER=s3
S3_CASE_FILES_BUCKET=cyphergy-documents
S3_REGION=us-east-1

# === EXTERNAL SERVICES ===
COURTLISTENER_API_URL=https://www.courtlistener.com/api/rest/v4
COURTLISTENER_API_KEY=<injected-from-secrets-manager>

# === CONNECTORS (Production tokens -- all injected from Secrets Manager) ===
# GMAIL_CREDENTIALS=<injected>
# GOOGLE_DRIVE_CREDENTIALS=<injected>
# ASANA_TOKEN=<injected>
# SLACK_BOT_TOKEN=<injected>
# NOTION_TOKEN=<injected>

# === FEATURE FLAGS (Progressive enable via admin panel) ===
DUAL_BRAIN_ENABLED=true
WDC_EXTENDED_PANEL=true
CRAWLER_ENABLED=true
HOLDING_EXTRACTION_ENABLED=true
ARGUMENT_GRAPH_ENABLED=true

# === CLOUDFLARE ===
CLOUDFLARE_ACCOUNT_ID=<in-github-secrets>
CLOUDFLARE_API_TOKEN=<in-github-secrets>

# === MODEL OVERRIDES (future rotation) ===
# MODEL_OVERRIDE_ORCHESTRATOR=anthropic.claude-opus-4-7-v1
# MODEL_OVERRIDE_JURISDICTION_SCOUT=meta.llama5-scout-v1:0
```

### Key Differences: Dev vs Staging vs Prod

```
+------------------------+---------------------------+------------------------------+-------------------------------+
|       Setting          |       Development         |          Staging             |         Production            |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Infrastructure         | Mac Docker Desktop        | ECS Fargate                  | ECS Fargate                   |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Database               | pgvector/pgvector:pg16    | RDS PostgreSQL               | RDS PostgreSQL                |
+------------------------+---------------------------+------------------------------+-------------------------------+
| LLM Provider           | Anthropic SDK (direct)    | AWS Bedrock                  | AWS Bedrock                   |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Orchestrator Model     | claude-opus-4-6 (API)     | anthropic.claude-opus-4-6-v1 | anthropic.claude-opus-4-6-v1  |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Fast Model             | claude-opus-4-6 (API)     | claude-haiku-4-5 (Bedrock)   | claude-haiku-4-5 (Bedrock)    |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Dual-Brain Scout       | claude-opus-4-6 (API)     | meta.llama4-scout (Bedrock)  | meta.llama4-scout (Bedrock)   |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Dual-Brain Cohere      | claude-opus-4-6 (API)     | cohere.command-r+ (Bedrock)  | cohere.command-r+ (Bedrock)   |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Secrets                | .env file                 | AWS Secrets Manager          | AWS Secrets Manager           |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Auth                   | Disabled (REQUIRE_AUTH=f)  | Enforced                     | Enforced                      |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Admin Auth             | ADMIN_JWT_SECRET (dev)    | ADMIN_JWT_SECRET (separate)  | ADMIN_JWT_SECRET (separate)   |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Beta Gate              | Disabled                  | Enabled (invite + IP lock)   | Enabled (invite + IP lock)    |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Feature Flags          | All ON (for testing)      | ALL OFF (test baseline)      | Progressive enable            |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Crawler                | Disabled                  | Disabled                     | Separate Fargate task         |
+------------------------+---------------------------+------------------------------+-------------------------------+
| CORS                   | localhost:3000/3001/5173  | staging.cyphergy.ai          | cyphergy.ai only              |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Rate Limiting          | Disabled                  | 30 req/min enforced          | 30 req/min enforced           |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Sentry                 | Off                       | On + PII scrubbing           | On + PII scrubbing            |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Debug Mode             | On (stack traces)         | Off (generic errors)         | Off (generic errors)          |
+------------------------+---------------------------+------------------------------+-------------------------------+
| DB Logging             | Echo all SQL              | Silent                       | Silent                        |
+------------------------+---------------------------+------------------------------+-------------------------------+
| File Storage           | Local volume              | S3 (encrypted)               | S3 (encrypted, locked)        |
+------------------------+---------------------------+------------------------------+-------------------------------+
| LLM Mock Mode          | Optional (for speed)      | Never                        | Never                         |
+------------------------+---------------------------+------------------------------+-------------------------------+
| JWT Expiration          | 60 min (dev convenience) | 30 min (security)            | 30 min (security)             |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Hot Reload             | Yes (volumes mounted)     | No (baked into image)        | No (baked into image)         |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Frontend               | npm run dev (:3000)       | Cloudflare Pages (staging)   | Cloudflare Pages (production) |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Admin Panel            | npm run dev (:3001)       | admin-staging.cyphergy.ai    | admin.cyphergy.ai             |
+------------------------+---------------------------+------------------------------+-------------------------------+
| WDC Gate               | None (Devin merges freely)| Score >= 7.5 + 1 approval    | Score >= 7.5 + manual + staging only |
+------------------------+---------------------------+------------------------------+-------------------------------+
| Deploy Trigger         | docker compose up         | merge to staging             | merge to main (from staging)  |
+------------------------+---------------------------+------------------------------+-------------------------------+
```

---

## 5. THE PROMOTION PROTOCOL (Dev -> Staging -> Prod)

```
DEVELOPER MACHINE (You / Devin)           STAGING (AWS)                   PRODUCTION (AWS)
================================          =================               ====================

1. Write code on feature branch
           |
           v
2. Pre-commit hooks run automatically
   +-- Linting (ruff)
   +-- Type checking (mypy)
   +-- Secrets scan (detect-secrets)
   +-- Unit tests (pytest tests/unit/)
   +-- FAIL? -> Cannot commit.
           |
           v
3. Push feature branch to GitHub
           |
           v
4. GitHub Actions: CI Pipeline fires
   +-- Build Docker image
   +-- Run ALL tests (pytest)
   +-- Security scan (bandit)
   +-- Install: pip install -e ".[dev]"
   +-- FAIL? -> PR blocked.
           |
           v
5. Open PR: feature/* -> dev
   +-- Devin merges freely (no WDC gate)
   +-- Tests must pass
   +-- Auto-review comment posted
           |
           v
6. Open PR: dev -> staging
           |
           v
7. WDC Gate fires (BLOCKING)
   +-- 5-agent scoring
   |   (Architect, Legal, Security,
   |    Quality, Red Team)
   +-- Composite score calculated
   +-- BELOW 7.5? -> PR blocked.
   +-- 1 approving review required
           |
           v
8. Merge to staging                  -------->  8a. Deploy to Staging Fargate
                                                +-- Build Docker image
                                                +-- Push to ECR
                                                +-- Update task definition
                                                +-- Rolling deploy
                                                +-- Smoke test
                                                +-- Feature flags: ALL OFF
                                                +-- Beta gate: ENABLED
           |
           v
9. Validate in staging
   +-- Test baseline (flags off)
   +-- Enable flags one at a time
   +-- Verify each flag in isolation
   +-- Admin panel manages beta invites
           |
           v
10. Open PR: staging -> main
           |
           v
11. WDC Gate fires (BLOCKING)
    +-- Composite score >= 7.5
    +-- Manual approval required
    +-- Source branch MUST be staging
    +-- FAIL? -> PR blocked.
           |
           v
12. Merge to main                                                       -------->  12a. Deploy to Production
                                                                                   +-- Build Docker image
                                                                                   +-- Push to ECR
                                                                                   +-- Update ECS task def
                                                                                   +-- Rolling deploy (zero downtime)
                                                                                   +-- Alembic migration (init container)
                                                                                   +-- Feature flags: progressive enable
                                                                                   +-- Beta gate: ENABLED
           |
           v
13. Smoke test on production
    +-- /health returns 200?
    +-- Can create a case?
    +-- Sentry: no P0 errors?
    +-- FAIL? -> Rollback (Section 13)
```

---

## 6. TEST GATES

### Gate 1: Pre-Commit (Local, Instant)

Must pass before `git commit` succeeds:

```
+---------------------+-----------------------------------------+----------+
|        Check        |              What It Does               | Blocking |
+---------------------+-----------------------------------------+----------+
| ruff check          | Linting + import sorting                | YES      |
+---------------------+-----------------------------------------+----------+
| ruff format --check | Code formatting                         | YES      |
+---------------------+-----------------------------------------+----------+
| mypy --strict       | Type checking                           | YES      |
+---------------------+-----------------------------------------+----------+
| detect-secrets scan | Catches API keys, passwords in code     | YES      |
+---------------------+-----------------------------------------+----------+
| pytest tests/unit/  | Unit tests only (fast, <30s)            | YES      |
+---------------------+-----------------------------------------+----------+
```

### Gate 2: CI Pipeline (GitHub Actions, On Push)

Must pass before PR can merge:

```
+--------------------------+------------------------------------+----------+
|          Check           |           What It Does             | Blocking |
+--------------------------+------------------------------------+----------+
| Docker build             | Image builds successfully          | YES      |
+--------------------------+------------------------------------+----------+
| pip install -e ".[dev]"  | Dependencies from pyproject.toml   | YES      |
+--------------------------+------------------------------------+----------+
| pytest tests/ --full     | ALL tests (unit + integration)     | YES      |
+--------------------------+------------------------------------+----------+
| bandit -r src/           | Security vulnerability scan        | YES      |
+--------------------------+------------------------------------+----------+
| Coverage >= 80%          | Test coverage threshold            | YES      |
+--------------------------+------------------------------------+----------+
| No HIGH/CRITICAL vulns   | Dependency vulnerability check     | YES      |
+--------------------------+------------------------------------+----------+
```

### Gate 3: WDC Review (Claude Code, On PR to staging/main)

Must pass before merge approval (NOT enforced on PRs to dev):

```
+--------------------------+------------------------------------+----------+
|          Check           |           What It Does             | Blocking |
+--------------------------+------------------------------------+----------+
| Architect score >= 7     | Fits Cyphergy architecture         | YES      |
+--------------------------+------------------------------------+----------+
| Legal Domain score >= 7  | Handles law correctly              | YES      |
+--------------------------+------------------------------------+----------+
| Security score >= 6      | No PII leaks, secrets, auth gaps   | AUTO-REJ |
+--------------------------+------------------------------------+----------+
| Composite >= 7.5         | Overall quality threshold          | YES      |
+--------------------------+------------------------------------+----------+
| No single agent below 4  | Nothing catastrophically wrong     | AUTO-REJ |
+--------------------------+------------------------------------+----------+
```

WDC models used for review panel:
- Primary (5 agents): `anthropic.claude-opus-4-6-v1` (all Opus for legal accuracy)
- Extended panel (WDC_EXTENDED_PANEL=true): adds Claude 4.5, Claude 4.1, Sonnet 4.6

### Gate 4: Post-Deploy Smoke (Staging + Production, After Deploy)

Must pass or trigger rollback:

```
+--------------------------+------------------------------------+----------+
|          Check           |           What It Does             | Blocking |
+--------------------------+------------------------------------+----------+
| GET /health -> 200       | API is alive                       | ROLLBACK |
+--------------------------+------------------------------------+----------+
| GET /health/ready -> 200 | LLM provider connected             | ROLLBACK |
+--------------------------+------------------------------------+----------+
| POST /api/cases -> 201   | Can create a case                  | ROLLBACK |
+--------------------------+------------------------------------+----------+
| Sentry: no P0 errors     | No critical errors in first 5 min  | ROLLBACK |
+--------------------------+------------------------------------+----------+
| Response time < 5s       | No severe latency                  | ALERT    |
+--------------------------+------------------------------------+----------+
| Beta gate functional     | Non-invited users get 403          | ROLLBACK |
+--------------------------+------------------------------------+----------+
```

---

## 7. GIT HOOKS

### Install Pre-Commit Framework

```bash
pip install pre-commit
```

### File: `.pre-commit-config.yaml` (Place in repo root)

```yaml
# ============================================
# CYPHERGY -- PRE-COMMIT HOOKS
# Install: pre-commit install
# Run manually: pre-commit run --all-files
# ============================================

repos:
  # --- Code Quality ---
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # --- Type Checking ---
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]
        args: [--ignore-missing-imports]

  # --- Secrets Detection ---
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]

  # --- General Hygiene ---
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: no-commit-to-branch
        args: [--branch, main, --branch, staging]    # Cannot commit directly to main or staging

  # --- Fast Unit Tests ---
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/unit/ -x -q --no-header
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
```

### Activate Hooks

```bash
# Run once after cloning the repo
pre-commit install

# Also install commit-msg hook for conventional commits
pre-commit install --hook-type commit-msg
```

### File: `.githooks/commit-msg` (Conventional Commit Enforcement)

```bash
#!/bin/bash
# Enforces conventional commit format:
# feat: / fix: / docs: / test: / refactor: / chore: / security:

COMMIT_MSG=$(cat "$1")
PATTERN="^(feat|fix|docs|test|refactor|chore|security|ci|build|perf)(\(.+\))?: .{1,72}"

if ! echo "$COMMIT_MSG" | grep -qE "$PATTERN"; then
  echo ""
  echo "ERROR: Commit message does not follow conventional format."
  echo ""
  echo "Required: type(scope): description"
  echo ""
  echo "Types: feat | fix | docs | test | refactor | chore | security | ci | build | perf"
  echo ""
  echo "Examples:"
  echo "  feat(agents): add opposing counsel simulation agent"
  echo "  fix(deadlines): correct Louisiana prescription computation"
  echo "  security(auth): enforce JWT expiration on all endpoints"
  echo "  test(citations): add CourtListener verification tests"
  echo ""
  echo "Your message: $COMMIT_MSG"
  echo ""
  exit 1
fi
```

### Activate Commit Message Hook

```bash
chmod +x .githooks/commit-msg
git config core.hooksPath .githooks
```

---

## 8. CLAUDE CODE HOOKS (WDC Integration)

These are commands you run in Claude Code as part of your workflow. They are not automated git hooks -- they are manual checkpoints in your dev process.

### Before Tasking Devin

```
Claude Code: "Task Devin on [feature]"
-> Claude Code produces a fenced DEVIN TASK spec
-> You paste it to Devin
-> Devin builds it
```

### After Devin Submits Code

```
Claude Code: "Review this" + paste Devin's output
-> Claude Code runs 5-agent WDC
-> Composite score determines action:
   7.5+ -> "Fix and merge"
   6.0-7.4 -> Claude Code fixes or re-tasks Devin
   <6.0 -> "Reject and re-task"
```

### Before Merging Any PR to Staging or Main

```
Claude Code: "Final review on PR #[X]"
-> Full WDC pass on the complete diff
-> Must score 7.5+ to approve
-> PRs to dev: informational only (no block)
-> PRs to staging: BLOCKING (WDC >= 7.5 + 1 approval)
-> PRs to main: BLOCKING (WDC >= 7.5 + manual approval + staging source only)
```

### Claude Code Quick Commands Reference

```bash
# Tasking
"Task Devin on [X]"              -> Generates DEVIN TASK spec
"Break [X] into Devin tasks"     -> Splits large feature into 1-3 tasks

# Reviewing
"Review this"                    -> Full 5-agent WDC review
"Quick review"                   -> Architect + Security only (fast check)
"Security review only"           -> Security agent deep dive

# Acting
"Fix and merge"                  -> Apply auto-fixes, commit, push
"Reject and re-task"             -> Write corrected DEVIN TASK
"Ship it"                        -> Tests + final WDC + merge to main

# Status
"Status"                         -> What's merged, pending, in Devin queue
"Test"                           -> Run pytest, report results
"Phase status"                   -> Current phase progress and blockers
```

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

---

## 9. GITHUB ACTIONS TRIGGERS

### File: `.github/workflows/ci.yml` (Runs on every push and PR)

```yaml
name: CI Pipeline

on:
  push:
    branches: [dev, staging, "feature/**"]
  pull_request:
    branches: [dev, staging, main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: cyphergy
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: cyphergy_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check src/ tests/

      - name: Format check (ruff)
        run: ruff format --check src/ tests/

      - name: Type check (mypy)
        run: mypy src/ --ignore-missing-imports

      - name: Security scan (bandit)
        run: bandit -r src/ -ll

      - name: Secrets scan
        run: detect-secrets scan --baseline .secrets.baseline

      - name: Run tests
        env:
          DATABASE_URL: postgresql://cyphergy:testpass@localhost:5432/cyphergy_test
          ENVIRONMENT: test
          JWT_SECRET_KEY: test-secret-key
          ADMIN_JWT_SECRET: test-admin-secret-key
          LLM_MOCK_MODE: "true"
          BETA_GATE_ENABLED: "false"
        run: pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80

      - name: Build Docker image
        run: docker build -t cyphergy-test .
```

### File: `.github/workflows/wdc-gate.yml` (WDC Merge Gate)

```yaml
name: WDC Merge Gate

on:
  pull_request:
    branches: [dev, staging, main]
  issue_comment:
    types: [created]

jobs:
  wdc-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Determine gate level
        id: gate
        run: |
          if [[ "${{ github.base_ref }}" == "dev" ]]; then
            echo "level=informational" >> $GITHUB_OUTPUT
            echo "blocking=false" >> $GITHUB_OUTPUT
          elif [[ "${{ github.base_ref }}" == "staging" ]]; then
            echo "level=staging" >> $GITHUB_OUTPUT
            echo "blocking=true" >> $GITHUB_OUTPUT
          elif [[ "${{ github.base_ref }}" == "main" ]]; then
            echo "level=production" >> $GITHUB_OUTPUT
            echo "blocking=true" >> $GITHUB_OUTPUT
          fi

      - name: WDC Review
        # 5-agent review using Opus 4.6 panel
        # Scoring: Architect (30%), Legal (25%), Security (20%), Quality (15%), Red Team (10%)
        # Threshold: composite >= 7.5, security >= 6, no agent below 4
        run: echo "WDC review runs here"

      - name: Enforce staging source (main only)
        if: github.base_ref == 'main'
        run: |
          HEAD_REF="${{ github.head_ref }}"
          if [[ "$HEAD_REF" != "staging" ]]; then
            echo "ERROR: PRs to main must originate from staging branch."
            echo "Source branch: $HEAD_REF"
            exit 1
          fi

      - name: Deletion guard
        run: |
          # Protect critical files from deletion
          PROTECTED="DOCS/ MEMORY.md GUARDRAILS.yml citation_chain.py deadline_calc.py wdc.py settings.py"
          # Check diff for deleted protected files
```

### File: `.github/workflows/deploy-production.yml` (Runs ONLY on merge to main)

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  # --- BACKEND: Build + Push + Deploy to Fargate ---
  deploy-backend:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, push to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/cyphergy-api:$IMAGE_TAG .
          docker push $ECR_REGISTRY/cyphergy-api:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/cyphergy-api:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Update ECS task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: infrastructure/ecs-task-definition.json
          container-name: cyphergy-api
          image: ${{ steps.build-image.outputs.image }}

      - name: Deploy to ECS Fargate
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: cyphergy-api
          cluster: cyphergy
          wait-for-service-stability: true

      - name: Smoke test
        run: |
          sleep 30
          curl -f https://api.cyphergy.ai/health || exit 1

  # --- FRONTEND: Build + Deploy to Cloudflare Pages ---
  deploy-frontend:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node 20
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install and build frontend
        working-directory: ./frontend
        run: |
          npm ci
          npm run build

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy frontend/dist --project-name=cyphergy
```

### File: `.github/workflows/deploy-staging.yml` (Runs on merge to staging)

```yaml
name: Deploy to Staging

on:
  push:
    branches: [staging]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, push to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: staging-${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/cyphergy-api:$IMAGE_TAG .
          docker push $ECR_REGISTRY/cyphergy-api:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/cyphergy-api:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Update ECS task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: infrastructure/ecs-task-definition.json
          container-name: cyphergy-api
          image: ${{ steps.build-image.outputs.image }}

      - name: Deploy to ECS Fargate (Staging)
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: cyphergy-api-staging
          cluster: cyphergy
          wait-for-service-stability: true

      - name: Smoke test
        run: |
          sleep 30
          curl -f https://api-staging.cyphergy.ai/health || exit 1
```

---

## 10. ADMIN PANEL DEPLOYMENT

The admin panel at `admin.cyphergy.ai` is a **completely separate** Cloudflare Pages project from the user-facing frontend at `cyphergy.ai`.

### Architecture

```
+-------------------------------------------+     +-------------------------------------------+
|  USER FRONTEND                             |     |  ADMIN PANEL                               |
|  cyphergy.ai (Cloudflare Pages)            |     |  admin.cyphergy.ai (Cloudflare Pages)      |
|  Project: cyphergy                         |     |  Project: admin-cyphergy                   |
|  Source: frontend/                          |     |  Source: admin/                             |
|  Auth: JWT_SECRET_KEY                      |     |  Auth: ADMIN_JWT_SECRET (DIFFERENT)         |
+-------------------------------------------+     +-------------------------------------------+
                     |                                              |
                     +---------------+  +---------------------------+
                                     |  |
                                     v  v
                          +----------------------------+
                          |  BACKEND API               |
                          |  api.cyphergy.ai           |
                          |  ECS Fargate               |
                          +----------------------------+
```

### Key Separation Rules

- `JWT_SECRET_KEY` != `ADMIN_JWT_SECRET` (always different keys)
- `ADMIN_EMAIL=bo@symio.ai` (hardcoded admin identity)
- Admin panel manages: beta invites, feature flags, user management, deployment stats, internal chat agent
- Admin panel has its own deployment workflow: `deploy-admin.yml`

### File: `.github/workflows/deploy-admin.yml` (Admin Panel Deploy)

```yaml
name: Deploy Admin Panel

on:
  push:
    branches: [main]
    paths:
      - 'admin/**'

jobs:
  deploy-admin:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node 20
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install and build admin panel
        working-directory: ./admin
        run: |
          npm ci
          npm run build

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy admin/dist --project-name=admin-cyphergy
```

### Beta Gate Flow

```
1. Admin (bo@symio.ai) logs into admin.cyphergy.ai
2. Admin creates beta invite -> generates invite code
3. User receives invite code
4. User registers with invite code at cyphergy.ai
5. On first login, user's IP is recorded and locked
6. All subsequent requests from that user must come from the locked IP
7. Admin can unlock/change IP via admin panel
8. If BETA_GATE_ENABLED=false (dev only), all access is unrestricted
```

---

## 11. BACKGROUND SERVICES (PERPETUAL CRAWLER)

The knowledge engine crawler runs as a **separate ECS Fargate task**, not inside the API container. It catalogs all case law from CourtListener (12M+ opinions), mapping every case to the statutes it interprets.

### Architecture

```
+---------------------------------+     +---------------------------------+
|  API SERVICE (Fargate)          |     |  CRAWLER SERVICE (Fargate)      |
|  Task: cyphergy-api             |     |  Task: cyphergy-crawler         |
|  Service: cyphergy-api          |     |  Service: cyphergy-crawler      |
|  Scaling: 1-4 tasks (ALB)      |     |  Scaling: 1 task (always-on)    |
|  CRAWLER_ENABLED: irrelevant    |     |  CRAWLER_ENABLED: true          |
|  Ports: 8000                    |     |  Ports: none (background)       |
+---------------------------------+     +---------------------------------+
            |                                        |
            v                                        v
+-----------------------------------------------------------------+
|  SHARED RESOURCES                                                |
|  +-- RDS PostgreSQL (pgvector for embeddings)                    |
|  +-- S3 cyphergy-documents (opinion text storage)                |
|  +-- CourtListener API (external data source)                    |
+-----------------------------------------------------------------+
```

### Crawler Task Definition

File: `infrastructure/ecs-crawler-task-definition.json`

```
Container:    cyphergy-crawler
Image:        222257058350.dkr.ecr.us-east-1.amazonaws.com/cyphergy-api:latest
Command:      ["python", "-m", "src.crawler.runner"]
CPU:          512
Memory:       1024
Environment:
  CRAWLER_ENABLED=true
  CRAWLER_MODE=perpetual
  CRAWLER_BATCH_SIZE=100
  CRAWLER_RATE_LIMIT=10/s
  LLM_PROVIDER=bedrock
  BEDROCK_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0
```

### Crawler Rules

```
+--------------------------+--------+---------+------------+
|         Setting          |  Dev   | Staging | Production |
+--------------------------+--------+---------+------------+
| CRAWLER_ENABLED          | false  | false   | true       |
+--------------------------+--------+---------+------------+
| Separate Fargate task    |  N/A   |  N/A    | YES        |
+--------------------------+--------+---------+------------+
| Uses Haiku (fast model)  |  N/A   |  N/A    | YES        |
+--------------------------+--------+---------+------------+
| Rate limit to CL API     |  N/A   |  N/A    | 10 req/s   |
+--------------------------+--------+---------+------------+
| Auto-restart on failure  |  N/A   |  N/A    | YES (ECS)  |
+--------------------------+--------+---------+------------+
```

### What the Crawler Does

1. Queries CourtListener API for opinions not yet cataloged
2. Downloads full opinion text, stores in S3
3. Extracts statutes cited in each opinion
4. Tags party support: `SUPPORTS_PLAINTIFF` / `SUPPORTS_DEFENDANT`
5. Generates vector embeddings (pgvector) for semantic search
6. Extracts holdings (when `HOLDING_EXTRACTION_ENABLED=true`)
7. Builds argument graph edges (when `ARGUMENT_GRAPH_ENABLED=true`)
8. Runs perpetually until ALL case law is cataloged
9. After initial catalog, switches to delta mode (new opinions only)

---

## 12. FEATURE FLAG PROGRESSIVE ROLLOUT

Feature flags control the activation of advanced capabilities. The rollout strategy differs by environment to ensure stability.

### Flag Inventory

```
+--------------------------------+-------+---------+----------------------------+
|           Flag                 |  Dev  | Staging |       Production           |
+--------------------------------+-------+---------+----------------------------+
| DUAL_BRAIN_ENABLED             |  ON   |   OFF   | Enable after single-agent  |
|                                |       |         | verified in staging        |
+--------------------------------+-------+---------+----------------------------+
| WDC_EXTENDED_PANEL             |  ON   |   OFF   | Enable after base WDC      |
|                                |       |         | verified in staging        |
+--------------------------------+-------+---------+----------------------------+
| CRAWLER_ENABLED                |  OFF  |   OFF   | Enable after DB + S3       |
|                                |       |         | verified in staging        |
+--------------------------------+-------+---------+----------------------------+
| HOLDING_EXTRACTION_ENABLED     |  ON   |   OFF   | Enable after crawler       |
|                                |       |         | verified in production     |
+--------------------------------+-------+---------+----------------------------+
| ARGUMENT_GRAPH_ENABLED         |  ON   |   OFF   | Enable after holdings      |
|                                |       |         | verified in production     |
+--------------------------------+-------+---------+----------------------------+
```

### Rollout Order (Production)

Flags must be enabled in this exact sequence. Each flag must be validated before enabling the next.

```
1. Baseline (all flags OFF)
   -> Verify: API healthy, cases create/read, auth works, beta gate works
   |
   v
2. DUAL_BRAIN_ENABLED = true
   -> Verify: 3-model consensus (Opus + Llama Scout + Cohere Command-R+)
   -> Verify: Fallback to single-model if one provider fails
   -> Monitor: Sentry for model timeout errors, latency < 15s
   |
   v
3. WDC_EXTENDED_PANEL = true
   -> Verify: Extended 8-model WDC panel produces valid scores
   -> Verify: Score variance within acceptable range
   -> Monitor: WDC review latency, score distribution
   |
   v
4. CRAWLER_ENABLED = true
   -> Verify: Crawler Fargate task starts and connects to RDS
   -> Verify: CourtListener API rate limiting respected
   -> Verify: Opinions stored in S3, indexed in pgvector
   -> Monitor: Crawler progress, DB connection pool, S3 costs
   |
   v
5. HOLDING_EXTRACTION_ENABLED = true
   -> Verify: Holdings extracted from crawled opinions
   -> Verify: Statute-to-case mappings populated
   -> Monitor: Extraction accuracy, processing time per opinion
   |
   v
6. ARGUMENT_GRAPH_ENABLED = true
   -> Verify: Directed case relationships built
   -> Verify: Graph queries return valid paths
   -> Monitor: Graph size, query latency
```

### How Flags Are Managed

- **Dev**: Hardcoded in `.env.development` (all ON except crawler)
- **Staging**: Hardcoded in ECS task definition (all OFF)
- **Production**: Managed via admin panel at `admin.cyphergy.ai`
  - Admin toggles flag -> updates ECS environment variable -> triggers rolling restart
  - Each flag change is logged with timestamp and admin identity
  - Rollback: disable flag -> rolling restart (< 3 minutes)

---

## 13. EMERGENCY ROLLBACK PROTOCOL

If production breaks after a deploy:

### Instant Rollback (< 2 minutes)

```bash
# 1. Find the last working image
aws ecs describe-services --cluster cyphergy --services cyphergy-api \
  --query 'services[0].deployments[*].taskDefinition'

# 2. Rollback to previous task definition
aws ecs update-service --cluster cyphergy --service cyphergy-api \
  --task-definition cyphergy-api:<PREVIOUS_REVISION_NUMBER> \
  --force-new-deployment

# 3. Verify
aws ecs wait services-stable --cluster cyphergy --services cyphergy-api
curl -f https://api.cyphergy.ai/health
```

### Git Rollback

```bash
# Revert the merge commit on main
git revert HEAD --no-edit
git push origin main
# GitHub Actions will deploy the reverted code automatically
```

### Frontend Rollback (Cloudflare)

```bash
# Cloudflare Pages keeps every deploy. Roll back in dashboard:
# Cloudflare -> Pages -> cyphergy -> Deployments -> Click previous -> "Rollback to this deploy"

# Admin panel rollback is separate:
# Cloudflare -> Pages -> admin-cyphergy -> Deployments -> Click previous -> "Rollback to this deploy"
```

### Staging Rollback

```bash
# Same as production but with staging service
aws ecs update-service --cluster cyphergy --service cyphergy-api-staging \
  --task-definition cyphergy-api:<PREVIOUS_REVISION_NUMBER> \
  --force-new-deployment
```

### Crawler Rollback

```bash
# Stop the crawler task
aws ecs update-service --cluster cyphergy --service cyphergy-crawler \
  --desired-count 0

# Or rollback to previous task definition
aws ecs update-service --cluster cyphergy --service cyphergy-crawler \
  --task-definition cyphergy-crawler:<PREVIOUS_REVISION_NUMBER> \
  --force-new-deployment --desired-count 1
```

### Circuit Breaker

```bash
# Rate limiter auto-trips at 5000 req/min global -> returns 503
# Manual reset via admin panel or ECS task restart

# Kill switch: set maintenance mode
# Update ECS task definition: APP_ENV=maintenance -> returns 503 to all requests
```

---

## SUMMARY: THE COMPLETE FLOW

```
You write code (or Devin does)
         |
         v
Pre-commit hooks catch garbage before it enters git
         |
         v
Push to feature branch
         |
         v
GitHub Actions CI runs full test suite (pyproject.toml, pgvector)
         |
         v
Open PR -> dev (Devin merges freely, no WDC gate)
         |
         v
Open PR -> staging (WDC score >= 7.5 + 1 approval)
         |
         v
Deploy to staging Fargate (all feature flags OFF, beta gate ON)
         |
         v
Validate baseline, then enable flags one at a time
         |
         v
Open PR -> main (WDC score >= 7.5 + manual approval, staging source only)
         |
         v
GitHub Actions deploys:
+-- Frontend -> Cloudflare Pages: cyphergy.ai (30 seconds)
+-- Admin -> Cloudflare Pages: admin.cyphergy.ai (separate workflow)
+-- Backend -> ECR -> ECS Fargate (3 minutes)
+-- Crawler -> Separate Fargate task (production only)
         |
         v
Smoke test on production
         |
         v
Progressive feature flag rollout via admin panel
         |
         v
Live. If broken -> Rollback in < 2 minutes.
```

---

## SECURITY GATES

| Gate | Where | What It Blocks |
|------|-------|---------------|
| LLM Guardrails | Orchestrator | Jailbreaks, model identity leaks, architecture leaks |
| No-Placeholders Hook | Claude Code | Fake data, demo content, placeholder text |
| WDC Merge Gate | GitHub Actions | PRs to staging/main without WDC score >= 7.5 |
| Deletion Guard | GitHub Actions | Protected file deletions |
| Beta Gate | API Middleware | Non-invited users, wrong IP |
| IP Lock | API Middleware | Requests from non-locked IP after first login |
| Rate Limiter | API Middleware | 4-layer: IP -> user -> tenant -> global |
| Source Protection | Cloudflare WAF | Source maps, webpack artifacts |
| JWT Auth | API Middleware | Unsigned/expired tokens |
| Admin Auth | API Middleware | Non-admin access to /admin/* (separate secret) |
| Bandit | CI Pipeline | Code-level security vulnerabilities |
| Gitleaks | CI Pipeline | Accidentally committed secrets |

---

## HEALTH CHECKS

```
GET /health           -> {"status": "ok", "agents": 5, "tests_passing": 33}
GET /health/ready     -> {"ready": true, "provider": "bedrock"}
```

ECS health check: `curl -f http://localhost:8000/health || exit 1` (30s interval, 5s timeout, 3 retries)

---

## GIT BRANCH PROTECTION (Enforced via GitHub API)

```
dev:
  - Required checks: CI Pipeline
  - No WDC gate (Devin merges freely)
  - Force push: blocked
  - Deletions: blocked

staging:
  - Required checks: "WDC Gate (staging)", "Deletion Protection", CI Pipeline
  - 1 approving review
  - Enforce admins: true
  - Force push: blocked
  - Deletions: blocked

main:
  - Required checks: "WDC Gate (main -- production)", "Deletion Protection", CI Pipeline
  - 1 approving review + admin enforcement
  - Enforce admins: true
  - Force push: blocked
  - Deletions: blocked
  - Only staging can merge to main
```

---

**Development is for speed. Staging is for validation. Production is for safety. The gates between them are non-negotiable.**

*Code fast locally. Validate in staging. Deploy with confidence. Roll back without panic.*
