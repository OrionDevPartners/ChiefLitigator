# CYPHERGY — COMPREHENSIVE ROADMAP TO FINISH LINE
# Owner: Bo Pennington | bo@symio.ai
# Created: 2026-03-17
# Current State: 79,982 lines / 330 files / 33 tests / 63 commits

---

## WHERE WE ARE NOW

```
BUILT:
  ✅ 5-agent orchestrator with WDC debate (17,060 lines Python)
  ✅ Bedrock Opus 4.6 + Llama Scout + Cohere R+ (all LIVE via Converse API)
  ✅ Citation Verification Chain (5-step, external retrieval enforced)
  ✅ Deadline Calculator (17 tests, 6 jurisdictions)
  ✅ 57 jurisdiction containers (50 states + federal + DC + 5 territories)
  ✅ Knowledge engine (crawler, catalog, holding extractor, argument graph)
  ✅ Admin panel + beta gate (IP locking, invite-only)
  ✅ LLM guardrails (3-layer: input + system prompt + output scrub)
  ✅ V0 frontend (chat, dashboard, onboarding, citations, deadlines)
  ✅ Docker isolation (Postgres pgvector + Redis + n8n)
  ✅ CI/CD (GitHub Actions, WDC merge gate, Trust but Verify branching)
  ✅ AWS (ECR, ECS cluster, ALB, RDS, S3, Secrets Manager, task def v3)
  ✅ Cloudflare (cyphergy.ai ACTIVE, admin.cyphergy.ai, Pages, WAF, SSL)
  ✅ Bedrock Core (Agent PREPARED, Guardrail v1 PUBLISHED)
  ✅ Dev-to-production protocol v2 (all 9 WDC fixes applied)
  ✅ 4 CPAA hooks enforced

BLOCKING PRODUCTION:
  ❌ ECS container won't start (Bedrock provider check fix committed but not pushed to ECR)
  ❌ Docker image needs amd64 rebuild for Fargate
  ❌ 9 uncommitted files in repo
```

---

## PHASE 1: GET TO PRODUCTION (Days 1-3)
### Goal: First user hits cyphergy.ai and gets a real Bedrock response

### 1.1 Fix + Deploy Backend (Day 1)
- [ ] Commit src/api.py fix (Bedrock provider needs no API key)
- [ ] Commit security audit + orphan files
- [ ] Push to dev
- [ ] Rebuild Docker image for linux/amd64: `docker build --platform linux/amd64`
- [ ] Push to ECR
- [ ] Force ECS redeploy with task def v3
- [ ] Verify: `curl https://api.cyphergy.ai/health` returns 200
- [ ] Verify: ECS running count = 1

### 1.2 Deploy Frontend (Day 1)
- [ ] Connect GitHub → Cloudflare Pages (cyphergy project → frontend/)
- [ ] Connect GitHub → Cloudflare Pages (admin-cyphergy project → admin-frontend/)
- [ ] Verify: https://cyphergy.ai loads the chat UI
- [ ] Verify: https://admin.cyphergy.ai loads the admin panel

### 1.3 Database Migration (Day 1)
- [ ] RDS security group: allow ECS task SG inbound on 5432
- [ ] Run alembic migration via ECS exec or one-off task
- [ ] Verify: tables created (users, cases, messages, deadlines, beta_invites)

### 1.4 First End-to-End Test (Day 2)
- [ ] Create admin account via API: POST /api/v1/auth/signup
- [ ] Login: POST /api/v1/auth/login → get JWT
- [ ] Send chat message: POST /api/v1/chat with Bearer token
- [ ] Verify: Bedrock Opus 4.6 responds with legal analysis
- [ ] Verify: LLM guardrails scrub any model identity leaks

### 1.5 Beta Gate Active (Day 2)
- [ ] Admin login at admin.cyphergy.ai
- [ ] Invite first beta user
- [ ] Beta user logs in → IP locked
- [ ] Verify: login from different IP → 403

### 1.6 Monitoring (Day 2)
- [ ] Create Sentry project → get DSN → add to Secrets Manager
- [ ] Verify: errors appear in Sentry dashboard
- [ ] Verify: CloudWatch logs flowing from ECS
- [ ] Set up AWS Budget alert ($100/month threshold)

### 1.7 Promote to Main (Day 3)
- [ ] PR dev → staging (WDC gate passes)
- [ ] PR staging → main (manual approval)
- [ ] Deploy workflow triggers → frontend + backend auto-deploy
- [ ] Smoke test on production

---

## PHASE 2: STABILIZE BETA (Week 1-2)
### Goal: 5 beta users running cases, no crashes, feedback loop active

### 2.1 Core Functionality
- [ ] Full 5-agent WDC debate: user asks → all agents respond → debate → certified output
- [ ] Case persistence: create, save, reload cases between sessions
- [ ] Message history: scroll through conversation with an agent
- [ ] Deadline tracking: add deadlines, get alerts
- [ ] Citation verification: every citation checked against CourtListener

### 2.2 Quality
- [ ] Fix all mypy type errors (Devin tasked — PR pending)
- [ ] Increase test coverage: 33 → 100+ tests
- [ ] Integration tests: real Bedrock call → real CourtListener lookup → real response
- [ ] Error Museum: document every bug found during beta

### 2.3 Performance
- [ ] Response time target: < 10s for chat, < 5s for deadline, < 3s for citation verify
- [ ] Rate limiting tuned for beta volume
- [ ] Cost tracking: Bedrock API spend per user per day

### 2.4 User Feedback
- [ ] Feedback form in UI (V0 component)
- [ ] Weekly beta user call (manual)
- [ ] Bug/feature tracking in Linear

---

## PHASE 3: KNOWLEDGE ENGINE LIVE (Week 3-4)
### Goal: Perpetual crawler running, case law cataloging, dual-brain active

### 3.1 Start Crawler
- [ ] Deploy crawler as background ECS task (separate from API)
- [ ] Start with SCOTUS (Supreme Court) cases
- [ ] Expand to federal circuit courts
- [ ] Expand to state supreme courts
- [ ] Monitor: cases cataloged per hour, CourtListener rate limits

### 3.2 Semantic Holding Extraction
- [ ] Enable dual-brain extraction on crawled cases
- [ ] Opus 4.6 + Llama Scout + Cohere extract independently
- [ ] 3-model consensus required for verified holdings
- [ ] Store in Aurora PostgreSQL (not in-memory)

### 3.3 Argument Graph
- [ ] Build graph edges as cases are cataloged (SUPPORTS/WEAKENS/OVERRULES)
- [ ] Enable argument chain generation for user queries
- [ ] V0: argument graph visualization component

### 3.4 Aurora Migration
- [ ] Move knowledge engine from in-memory to Aurora PostgreSQL
- [ ] Enable pgvector for semantic search of holdings
- [ ] Cloudflare Vectorize as edge cache for frequent searches

---

## PHASE 4: JURISDICTION DEPTH (Week 5-8)
### Goal: All 57 containers populated with verified case law

### 4.1 Overlap Rules
- [ ] Complete overlap rules for all 50 states (currently 5 states done)
- [ ] Each state: punitive damages gate, RICO applicability, fraud civil/criminal
- [ ] Federal: complete FCA, RICO, forfeiture rules

### 4.2 Deadline Calculator Expansion
- [ ] Expand from 6 jurisdictions to all 50 states + federal
- [ ] Add: state-specific holiday calendars
- [ ] Add: local court rules (individual judge standing orders)
- [ ] Target: 100+ deadline tests

### 4.3 Predictive Outcome Modeling
- [ ] Tag crawled cases: plaintiff-win vs defendant-win
- [ ] Compute win probability per statute per jurisdiction
- [ ] Display in case dashboard
- [ ] Requires: 1000+ cases per jurisdiction minimum for statistical significance

### 4.4 Cross-Jurisdiction Conflict Router
- [ ] Meta-container for choice-of-law analysis
- [ ] Query multiple containers simultaneously
- [ ] Reconcile conflicting law between jurisdictions

---

## PHASE 5: DOCUMENT GENERATION (Week 6-8)
### Goal: Court-ready .docx/.pdf filings

### 5.1 Template Engine
- [ ] docxtpl for DOCX rendering
- [ ] WeasyPrint for PDF generation
- [ ] Court-specific format profiles (federal + state)

### 5.2 Document Types
- [ ] Complaints / petitions
- [ ] Motions (dismiss, compel, summary judgment)
- [ ] Discovery (interrogatories, RFPs, RFAs)
- [ ] Demand letters
- [ ] Settlement agreements

### 5.3 Document Pipeline
- [ ] Draft → Red Team review → Compliance check → WDC score → deliver
- [ ] E-filing format validation (PDF/A)
- [ ] Exhibit preparation (Bates numbering)

---

## PHASE 6: INTEGRATIONS (Week 7-9)
### Goal: Connected to all external legal data sources

### 6.1 Legal Data
- [ ] CourtListener MCP server (custom-built)
- [ ] US Code API integration
- [ ] eCFR API integration
- [ ] PACER integration (federal court filings)
- [ ] State court portal connectors

### 6.2 Productivity
- [ ] Google Drive (case file storage)
- [ ] Google Calendar (deadline reminders)
- [ ] Gmail (correspondence)
- [ ] n8n workflows (automated alerts, case intake)

### 6.3 Business
- [ ] Stripe (payment processing for Pro tier)
- [ ] SES (email notifications)
- [ ] Step Functions (production workflow automation)

---

## PHASE 7: FRONTEND POLISH (Week 8-10)
### Goal: Production-quality UI that makes Westlaw look like 1995

### 7.1 User UI (V0)
- [ ] Argument graph visualization
- [ ] Case timeline (interactive)
- [ ] Evidence inventory manager
- [ ] Document viewer with confidence flags
- [ ] Mobile-responsive (all screens)

### 7.2 Admin Panel (V0)
- [ ] Full analytics dashboard (users, cases, API cost, WDC pass rate)
- [ ] Connector management
- [ ] Agent observatory (live agent status)
- [ ] Deployment panel (git + redeploy from admin)
- [ ] Internal chat agent (Bedrock AgentCore)

### 7.3 Mobile App
- [ ] Expo React Native scaffold
- [ ] 5-tab navigation (Cases, Chat, Deadlines, Documents, Settings)
- [ ] Offline courtroom mode (cached case data)
- [ ] Zero marketing in app

### 7.4 Onboarding
- [ ] 5-step flow (sign up → intent → interview → dashboard → first deliverable)
- [ ] 14-day reverse trial (Pro features → downgrade to Free)
- [ ] First value in 5 minutes

---

## PHASE 8: PRODUCTION HARDENING (Week 9-11)
### Goal: Enterprise-ready security and compliance

### 8.1 Testing
- [ ] 200+ tests (unit + integration + adversarial + E2E)
- [ ] 10 anonymized real case scenarios (full lifecycle)
- [ ] Citation accuracy audit: 100% verified in test outputs
- [ ] Deadline computation: verified against known court calendars
- [ ] Load testing + cost optimization

### 8.2 Compliance
- [ ] SOC 2 Type II documentation
- [ ] EU AI Act Article 9/11 conformity docs
- [ ] HIPAA BAA with Anthropic/AWS
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Formal STRIDE threat model
- [ ] E&O insurance

### 8.3 Security
- [ ] Annual penetration testing schedule
- [ ] Dependency scanning (automated weekly)
- [ ] Secret rotation policy (90-day JWT keys)
- [ ] Incident response playbook tested

---

## PHASE 9: SCALE + DIFFERENTIATE (Week 12+)
### Goal: Per-jurisdiction AI that outperforms general-purpose models

### 9.1 Jurisdiction Fine-Tuning
- [ ] Custom Model Import: HuggingFace → Bedrock
- [ ] First model: Louisiana (home jurisdiction)
- [ ] Training data: WDC debate transcripts + case outcomes + corrections
- [ ] Benchmark: per-jurisdiction accuracy vs general Opus 4.6

### 9.2 Model Distillation
- [ ] Train smaller models from Opus 4.6 teacher outputs
- [ ] Cost reduction: $0.015/query → $0.001/query for routine tasks
- [ ] Deploy via Bedrock Core provisioned throughput

### 9.3 Cloudflare Edge
- [ ] Workers AI for edge inference (classification, embeddings)
- [ ] Vectorize for citation semantic search at edge
- [ ] R2 for document storage (S3-compatible, no egress fees)

### 9.4 Revenue
- [ ] Pricing live: Free ($0) / Pro ($29) / Team ($49/user) / Enterprise
- [ ] Content marketing + legal forum SEO
- [ ] Legal aid organization partnerships
- [ ] Beta → public launch

---

## METRICS TARGETS

| Metric | Now | Beta | Production | Scale |
|--------|-----|------|-----------|-------|
| Python lines | 17,060 | 20,000 | 25,000 | 35,000 |
| Tests | 33 | 100 | 200 | 500 |
| Cases cataloged | 0 | 1,000 | 100,000 | 12,000,000 |
| Statutes indexed | 0 | 100 | 5,000 | 100,000 |
| Jurisdictions active | 0 | 5 | 20 | 57 |
| Users | 0 | 5 | 50 | 1,000 |
| Response time | N/A | <10s | <5s | <3s |
| Citation accuracy | N/A | 95% | 99% | 99.9% |
| Deadline accuracy | 100% (tests) | 100% | 100% | 100% |
| Uptime | N/A | 95% | 99.5% | 99.9% |
| Monthly API cost | $0 | $50 | $500 | $5,000 |

---

## HARD MANDATES (ALL PHASES)

1. No placeholders/filler/simulations/demo data — EVER (hook enforced)
2. No AI attribution in commits (@M:014)
3. Citation verification: external text only, never model memory
4. Deadline computation: conservative (earlier date when ambiguous)
5. Admin panel fully disconnected from user UI
6. DEV: Anthropic/Bedrock. PROD: Bedrock Core (best per agent class)
7. All CI quality gates enforced — no continue-on-error
8. All UI via V0 — no hand-written components
9. LLM guardrails: models never reveal maker/model/architecture
10. No cross-contamination with Symio or other projects
11. NEVER create files outside CIPHERGY/ repo directory
12. NEVER delete — always archive

---

## THE FINISH LINE

```
PRODUCTION LAUNCH = when all of these are true:
  ✅ ECS container running + health check passing
  ✅ cyphergy.ai serves V0 frontend
  ✅ api.cyphergy.ai responds to authenticated requests
  ✅ Bedrock Opus 4.6 generates legal analysis
  ✅ Citations verified against CourtListener
  ✅ Deadlines computed correctly for user's jurisdiction
  ✅ Case data persists between sessions
  ✅ Admin panel works at admin.cyphergy.ai
  ✅ Beta gate enforces IP locking
  ✅ LLM guardrails prevent identity leaks
  ✅ Sentry captures errors (PII scrubbed)
  ✅ 100+ tests passing
  ✅ Cost < $500/month for first 50 users
```

**Phase 1 (Days 1-3) is the critical path.**
Everything else builds on a working deployment.

---

*Cyphergy — Five AI Minds. Fifty-Seven Jurisdictions. One Mission.*
*Property of Bo Pennington / OrionDevPartners.*
