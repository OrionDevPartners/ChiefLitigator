# ChiefLitigator — Production Deployment Roadmap

**Target:** Live at `chieflitigator.com` and `chieflitigator.ai`
**Methodology:** Portwave Cascade (Scope-first, Parallel Runners, No Linear Timelines)
**Current State:** 166 Python files, 44,745 LOC. Core engines built. API layer built.

This roadmap defines the exact scope required to move from the current codebase to a live, revenue-generating production deployment. Execution will occur via parallel runners, not sequential steps.

---

## 1. The Infrastructure Runner (AWS + Cloudflare)

**Scope:** Stand up the physical and virtual infrastructure to host the application.

- [ ] **AWS Bedrock Provisioning**
  - Request model access for Claude 3.5 Sonnet/Opus, Llama 3, and Cohere Command R+ in `us-east-1` or `us-west-2`.
  - Configure Bedrock Guardrails (PII redaction, content filtering).
  - Provision Titan Embeddings V2 endpoint.
- [ ] **AWS Aurora PostgreSQL (pgvector)**
  - Provision Aurora Serverless v2 cluster.
  - Enable `pgvector` extension.
  - Run Alembic migrations to create `Statute`, `CaseLaw`, and `CourtRule` tables.
- [ ] **AWS DynamoDB**
  - Provision `ChiefLitigator_Sessions`, `ChiefLitigator_Cases`, and `ChiefLitigator_GalvanizerLogs` tables.
  - Configure TTL for session data.
- [ ] **AWS ECS Fargate**
  - Update `infrastructure/ecs-task-definition.json` with new environment variables.
  - Provision Application Load Balancer (ALB) and Target Groups.
- [ ] **Cloudflare Routing**
  - Connect `chieflitigator.com` and `chieflitigator.ai` domains.
  - Configure WAF rules (`infrastructure/cloudflare-waf-rules.json`).
  - Set up routing: `/api/*` to AWS ALB, `/` to Vercel/Cloudflare Pages (Frontend).

---

## 2. The Data Siphon Runner (Knowledge Graph)

**Scope:** Populate the Aurora pgvector database with the foundational legal knowledge required for the If-Then Matching Engine.

- [ ] **CourtListener Bulk Ingest**
  - Execute `src/siphon/courtlistener_worker.py` to pull the 8M+ opinion dataset.
  - Generate embeddings via Bedrock Titan and store in Aurora.
- [ ] **US Code Ingest**
  - Execute `src/siphon/uscode_worker.py` to pull all 54 titles from OLRC.
  - Chunk, embed, and store.
- [ ] **State Statutes & Rules**
  - Build and execute LegiScan worker for 50-state statutes.
  - Build and execute GovInfo worker for Federal Rules of Civil Procedure (FRCP).
- [ ] **EventBridge Scheduling**
  - Configure AWS EventBridge to trigger the `SiphonOrchestrator` daily for incremental updates.

---

## 3. The Frontend Runner (Next.js UI)

**Scope:** Connect the existing Next.js frontend components to the new FastAPI backend.

- [ ] **API Client Wiring**
  - Update `frontend/app/api/chat/route.ts` to point to the new `/api/v1/chat` endpoint.
  - Wire the `CaseSummary` and `ClaimsMatrix` components to `/api/v1/cases/{id}`.
  - Wire the `DocumentUpload` component to `/api/v1/documents/upload`.
- [ ] **The Galvanizer UI**
  - Build the real-time debate viewer component (showing Advocacy vs. Stress-Test panels).
  - Implement the 90% Confidence Ring visualization.
- [ ] **Authentication & Onboarding**
  - Implement Clerk or Auth0 for user management.
  - Connect the `Step1SignUp` through `Step5Deliverable` onboarding flow to the `IntakeAgent`.
- [ ] **Deployment**
  - Deploy the Next.js app to Cloudflare Pages or Vercel.
  - Configure environment variables (`NEXT_PUBLIC_API_URL`).

---

## 4. The Integration Runner (Court Portals)

**Scope:** Finalize the connections to external court systems for e-filing and docket monitoring.

- [ ] **PACER Credentials**
  - Secure production PACER credentials and store in AWS Secrets Manager.
  - Test `PACERClient` authentication and docket retrieval.
- [ ] **State EFSP Certification**
  - Register as an EFSP with Tyler Technologies (Odyssey) for the 30+ supported states.
  - Secure API keys for eFileTexas, NYSCEF, and TrueFiling.
- [ ] **CourtListener Webhooks**
  - Configure CourtListener webhooks to push docket updates to the `DocketMonitor` agent.

---

## 5. The CI/CD & Security Runner

**Scope:** Ensure the deployment pipeline is robust, secure, and automated.

- [ ] **GitHub Actions**
  - Verify `.github/workflows/deploy-production.yml` successfully builds the Docker image and pushes to ECR.
  - Verify ECS deployment step triggers correctly on merge to `main`.
- [ ] **Secrets Management**
  - Audit codebase to ensure zero hardcoded secrets (already verified, but enforce via `security-scan.yml`).
  - Map all required environment variables in AWS Systems Manager Parameter Store.
- [ ] **WDC Merge Gate**
  - Enforce the `wdc-gate.yml` workflow: no code merges to `main` without a WDC score >= 7.5.

---

## Execution Protocol

1. **No Linear Dependencies:** All 5 runners can and should be executed concurrently.
2. **Militant Loop-Closing:** Every task completion must be logged in `EXECUTION_JOURNAL.md`.
3. **Zero Code Deletion:** Refactor and append only.
4. **Deploy Target:** Git → CI/CD → AWS (Backend) + Cloudflare (Frontend).
