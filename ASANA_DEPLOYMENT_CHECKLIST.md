# CYPHERGY — DEV TO PRODUCTION DEPLOYMENT CHECKLIST
# Copy into Asana as a project with sections + tasks
# Each section = Asana section. Each [ ] = Asana task.
# Last Updated: 2026-03-16

---

## SECTION 1: PRE-FLIGHT (Before any deployment work)

- [ ] Verify ANTHROPIC_API_KEY is in .env (dev)
- [ ] Verify DATABASE_URL is in .env (points to local Docker Postgres or RDS)
- [ ] Verify JWT_SECRET_KEY is in .env
- [ ] Verify ADMIN_JWT_SECRET is in .env (different from JWT_SECRET_KEY)
- [ ] Verify ADMIN_EMAIL=bo@symio.ai is in .env
- [ ] Verify Docker Desktop is running (M4 Max)
- [ ] Verify `git branch` shows `dev`
- [ ] Verify `python3 -m pytest tests/ -q` shows 33+ passed
- [ ] Verify `git status` shows clean working tree

---

## SECTION 2: LOCAL DEV ENVIRONMENT (Docker Desktop)

- [ ] Create `.env.development` from `.env.example` with local values
- [ ] Run `docker compose up -d` (API + Postgres + Redis)
- [ ] Verify `curl http://localhost:8000/health` returns 200
- [ ] Verify `curl http://localhost:8000/health/ready` shows provider info
- [ ] Run `alembic upgrade head` against local Postgres
- [ ] Test signup: `POST /api/v1/auth/signup` with test email
- [ ] Test login: `POST /api/v1/auth/login` returns JWT
- [ ] Test chat: `POST /api/v1/chat` with Bearer token → real LLM response
- [ ] Test citation: `POST /api/v1/verify-citation` with real citation
- [ ] Test deadline: `POST /api/v1/compute-deadline` returns correct date
- [ ] Test jurisdiction query: `POST /api/v1/jurisdiction/query` with "LA"
- [ ] Verify LLM guardrails: send jailbreak prompt → blocked
- [ ] Verify admin login: `POST /admin/login` with admin credentials
- [ ] Run full test suite: `make ci` (lint + typecheck + test + security)

---

## SECTION 3: CI/CD PIPELINE VERIFICATION

- [ ] Push to `dev` branch triggers CI workflow
- [ ] CI: lint (ruff) passes
- [ ] CI: typecheck (mypy) passes
- [ ] CI: test (pytest) passes on Python 3.11 + 3.12
- [ ] CI: security scan (bandit) — 0 HIGH findings
- [ ] CI: secrets scan (gitleaks) — clean
- [ ] CI: Docker image builds successfully
- [ ] WDC merge gate workflow exists at `.github/workflows/wdc-gate.yml`
- [ ] Branch protection: staging requires WDC >= 7.5 + 1 approval
- [ ] Branch protection: main requires WDC >= 7.5 + 1 approval + admin

---

## SECTION 4: AWS INFRASTRUCTURE

- [ ] ECR repository exists: `cyphergy-api`
- [ ] ECS cluster exists: `cyphergy` (ACTIVE, Fargate)
- [ ] ECS task definition registered: `cyphergy-api:1`
- [ ] RDS PostgreSQL running: `cyphergy-beta` (available)
- [ ] S3 bucket exists: `cyphergy-documents` (encrypted, locked)
- [ ] CloudWatch log group: `/ecs/cyphergy-api`
- [ ] Security group: `cyphergy-ecs-sg` (port 8000)
- [ ] IAM role: `ecsTaskExecutionRole` with ECS policy
- [ ] RDS password set and in AWS Secrets Manager
- [ ] JWT secrets in AWS Secrets Manager

---

## SECTION 5: CLOUDFLARE INFRASTRUCTURE

- [ ] Zone `cyphergy.ai` status: ACTIVE
- [ ] DNS: `cyphergy.ai` CNAME → `cyphergy.pages.dev`
- [ ] DNS: `www.cyphergy.ai` CNAME → `cyphergy.pages.dev`
- [ ] DNS: `admin.cyphergy.ai` CNAME → `admin-cyphergy.pages.dev`
- [ ] SSL: strict mode enabled
- [ ] Always HTTPS: enabled
- [ ] Pages project: `cyphergy` (user frontend)
- [ ] Pages project: `admin-cyphergy` (admin panel)
- [ ] WAF rule: source maps blocked
- [ ] WAF rule: 10 security rules active
- [ ] Workers AI: available (88 models)
- [ ] Vectorize: available (ready for citation index)

---

## SECTION 6: FIRST DEPLOYMENT (Dev → Staging)

- [ ] Create PR: `dev` → `staging`
- [ ] PR triggers WDC merge gate
- [ ] WDC composite score >= 7.5
- [ ] 1 approving review on PR
- [ ] Merge PR to staging
- [ ] CI builds Docker image from staging
- [ ] Image pushed to ECR
- [ ] ECS task definition updated
- [ ] Create ECS Fargate service with ALB
- [ ] Alembic migration runs (init container or manual)
- [ ] Health check: `GET /health` returns 200 on staging
- [ ] Smoke test: create case, send chat message, verify response

---

## SECTION 7: STAGING → PRODUCTION

- [ ] All staging smoke tests passing
- [ ] Create PR: `staging` → `main`
- [ ] WDC merge gate: composite >= 7.5
- [ ] 1 approving review + admin enforcement
- [ ] PR source must be `staging` (not direct to main)
- [ ] Merge to main triggers deploy pipeline
- [ ] Docker image built and pushed to ECR
- [ ] ECS rolling deployment (zero downtime)
- [ ] Health check passes on production
- [ ] Sentry: no P0 errors in first 5 minutes
- [ ] Response time < 5 seconds

---

## SECTION 8: BETA GATE SETUP

- [ ] BETA_GATE_ENABLED=true in production env
- [ ] IP_LOCK_ENABLED=true in production env
- [ ] Admin panel accessible at admin.cyphergy.ai
- [ ] Admin login works with Bo's credentials
- [ ] Invite first beta user via admin panel
- [ ] Beta user receives email with credentials
- [ ] Beta user logs in → IP locked to first login IP
- [ ] Beta user accesses cyphergy.ai → clean UI, no source code visible
- [ ] Test: login from different IP → blocked with 403
- [ ] Test: send jailbreak prompt → blocked by guardrails

---

## SECTION 9: FEATURE FLAG ROLLOUT (Production)

- [ ] Baseline: all flags OFF → system works with basic chat
- [ ] Enable DUAL_BRAIN_ENABLED → verify 3-model consensus
- [ ] Enable WDC_EXTENDED_PANEL → verify 8-model scoring
- [ ] Enable CRAWLER_ENABLED → verify crawler starts cataloging
- [ ] Enable HOLDING_EXTRACTION_ENABLED → verify semantic extraction
- [ ] Enable ARGUMENT_GRAPH_ENABLED → verify graph building
- [ ] Monitor each flag for 24h before enabling next

---

## SECTION 10: POST-LAUNCH MONITORING

- [ ] Sentry dashboard showing live errors (PII scrubbed)
- [ ] CloudWatch logs flowing from ECS
- [ ] Admin panel: system health all green
- [ ] Admin panel: user count, case count visible
- [ ] Admin panel: agent status visible
- [ ] Rate limiter working (test with rapid requests)
- [ ] Citation verification working against CourtListener
- [ ] Deadline calculator returning correct dates
- [ ] WDC scoring every substantive output

---

## SECTION 11: EMERGENCY PROCEDURES (Reference)

- [ ] Document rollback command: `aws ecs update-service --task-definition cyphergy-api:PREV`
- [ ] Document git revert: `git revert HEAD && git push origin main`
- [ ] Document Cloudflare rollback: Pages dashboard → previous deploy
- [ ] Document circuit breaker: rate limiter trips at 5000 req/min → 503
- [ ] Document kill switch: APP_ENV=maintenance → 503 to all

---

## HARD MANDATES (Apply to ALL sections above)

1. No placeholders, filler, simulations, or demo data — EVER
2. No AI attribution in commits
3. Citation verification: external text only, never model memory
4. Deadline computation: conservative (earlier date when ambiguous)
5. Admin panel fully disconnected from user UI
6. All models attach via env mount only (CPAA enforced by hooks)
7. All CI quality gates enforced — no continue-on-error
8. All UI via V0 — no hand-written components
9. LLM guardrails: models never reveal maker/model/architecture
10. No cross-contamination with Symio or other projects
