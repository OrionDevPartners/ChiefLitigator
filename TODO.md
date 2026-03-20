# CYPHERGY — MASTER TODO (A to Z)
# Novel architecture by Bo Pennington
# Format: [ ] pending | [~] in-progress | [x] done | [!] blocked
# Last Updated: 2026-03-19

---

## PHASE 0: FOUNDATION [~85% COMPLETE]

### Agents + Orchestration
- [x] BaseAgent + provider adapter (Anthropic ↔ Bedrock CPAA switch)
- [x] 5 agents: Lead Counsel, Research, Drafting, Red Team, Compliance
- [x] WDC v2.0 engine (16 tests, veto, thresholds)
- [x] Full orchestration loop (fan-out → WDC debate → revision cycles)
- [x] LLM guardrails (3-layer: input gate + system prompt + output scrub)
- [x] Error handling + graceful degradation (failed agents don't block pipeline)
- [ ] Wire model_router.py into orchestrator (replace single-model with 3-tier)
- [ ] First real Bedrock API call through full pipeline (end-to-end proof)
- [ ] `src/providers/bedrock_agentcore.py` — AgentCore runtime: session mgmt, 8-hr sessions, multi-agent orchestration
- [ ] `src/providers/bedrock_tools.py` — Tool-use / function-calling layer via Converse API toolConfig
- [ ] `src/providers/bedrock_embeddings.py` — Titan Embeddings V2 for pgvector (1536-dim)
- [ ] `src/providers/bedrock_guardrails.py` — Bedrock Guardrails: content filtering + PII redaction

### API + Auth
- [x] FastAPI entrypoint (5 endpoints: health, chat, verify-citation, compute-deadline)
- [x] JWT auth middleware (Devin PR #4, merged)
- [x] User signup/login (bcrypt + JWT)
- [x] Auth router wired into api.py
- [x] Wire admin router into api.py
- [x] Wire beta gate middleware into api.py

### Database
- [x] PostgreSQL models (User, Case, Message, Deadline)
- [x] CRUD operations (async)
- [x] Alembic migrations configured
- [x] RDS provisioned (cyphergy-beta, available)
- [ ] Run alembic upgrade head on RDS (via ECS init container — VPC only)
- [ ] Case persistence endpoints (Devin PR #5, merged — wire into api.py)

### Verification + Legal
- [x] Citation Verification Chain (5-step, external-retrieval hard constraint)
- [x] Deadline Calculator (17 tests, 6 jurisdictions)
- [x] 57 jurisdiction containers (50 states + federal + DC + 5 territories)
- [x] Practice area split (civil, criminal, overlap + 28 sub-areas)
- [x] Overlap rules (FL § 768.72, CA § 3294, TX § 41.003, LA art. 2315.4, NY, FED RICO/FCA)

### Infrastructure
- [x] AWS: ECR, ECS cluster, S3 (encrypted), CloudWatch, RDS, SG, IAM, task def
- [x] Cloudflare: cyphergy.ai ACTIVE, admin.cyphergy.ai, Pages x2, SSL strict, WAF
- [x] CI/CD: GitHub Actions, WDC merge gate, Trust but Verify branching
- [x] Security: 4-layer rate limiter, middleware, secrets manager, no-placeholders hook
- [ ] Connect GitHub → Cloudflare Pages (both projects — CF dashboard)
- [ ] Create ECS Fargate service with ALB
- [ ] First deployment to ECS

### Frontend (V0 mandate — all UI via v0.dev)
- [x] Chat interface (9 files, wired to real API)
- [x] Case dashboard (11 files, props-based, no fake data)
- [x] Onboarding flow (10 files)
- [x] Source protection (no source maps, WAF blocks, security headers)
- [x] V0: Citation viewer component
- [x] V0: Deadline manager component
- [ ] V0: Admin dashboard (login, users, agents, deploy, chat)
- [ ] V0: Mobile app shell (Expo)

### The Galvanizer (Adversarial Panel Engine)
- [ ] `src/orchestrator/galvanizer.py` — Advocacy Panel vs Stress-Test Panel, iterative rounds, 90% confidence gate
- [ ] Integrate Galvanizer into WDC scoring pipeline
- [ ] Galvanizer debate transcript logging to DynamoDB
- [ ] Round-by-round confidence escalation tracking

### Intake Agent (Context-to-Law Matching)
- [ ] `src/agents/intake_agent.py` — NLP intake: extract facts, identify legal issues, route to matching engine
- [ ] Wire intake agent to If-Then Matching Engine (`src/matching/if_then_engine.py`)
- [ ] Plain-language response generation for pro se users
- [ ] Guided intake flow (eviction, immigration, liens, contract disputes, etc.)

### Document Generator
- [ ] `src/agents/document_generator.py` — Court-ready docs: Complaints, Answers, Motions, Notices, Liens, Immigration forms
- [ ] `src/templates/` — Court document templates per jurisdiction per document type
- [ ] PDF generation with court-specific formatting (margins, fonts, caption blocks)
- [ ] Document versioning with Galvanizer confidence scores

### Court Portal Connector
- [ ] `src/integrations/court_portal.py` — Universal e-filing abstraction layer
- [ ] `src/integrations/pacer_client.py` — PACER NextGen CM/ECF API client
- [ ] `src/integrations/efsp_router.py` — State EFSP routing (Tyler Odyssey, eFileTexas, etc.)
- [ ] Filing status tracking and confirmation

### Evidence Scorer
- [ ] `src/agents/evidence_scorer.py` — Score evidence strength, identify gaps, recommend additional evidence
- [ ] Hypothesis tracking with confidence scoring
- [ ] Evidence-to-claim mapping matrix
- [ ] Document OCR + privilege detection

### Docket Monitor
- [ ] `src/agents/docket_monitor.py` — Real-time docket monitoring via PACER RSS + CourtListener webhooks
- [ ] Auto-triggered workflows on new docket entries
- [ ] Deadline recalculation on docket changes

### Admin + Beta
- [x] Admin panel backend (separate auth, routes, internal chat agent, audit log)
- [x] Beta gate (IP locking, invite-only, email sender)
- [x] admin.cyphergy.ai DNS + Pages project
- [ ] Wire admin routes into separate FastAPI app (not shared with user API)
- [ ] Admin panel V0 frontend deployed to admin-cyphergy.pages.dev
- [ ] First beta user invited through admin panel

---

## PHASE 1: KNOWLEDGE ENGINE [~40% COMPLETE]

### Perpetual Crawler (exhaustive case law cataloging)
- [x] CaseLawCrawler — perpetual background crawler via CourtListener API
- [x] CaseLawEntry — lightweight: case#, date, parties, links, holdings, tags
- [x] StatuteIndex — every statute mapped to interpreting case law
- [x] CaseCatalog — two modes: context-aware + context-free search
- [x] PartyRole tags (SUPPORTS_PLAINTIFF / SUPPORTS_DEFENDANT)
- [x] Positive/negative tags for instant matching
- [ ] Deploy crawler as background ECS task (perpetual, resumable)
- [ ] Crawl ALL Supreme Court cases (start with SCOTUS → circuit → state)
- [ ] Crawl ALL state supreme court cases (50 states)
- [ ] Crawl ALL state appellate court cases
- [ ] Crawl ALL federal circuit court cases (1st-11th + DC + Federal)
- [ ] Crawl ALL federal district court cases
- [ ] Aurora PostgreSQL storage for catalog (not in-memory)
- [ ] Cloudflare Vectorize for semantic search of holdings

### Semantic Holding Extraction (UPGRADE #1)
- [x] Semantic holding extraction engine built (src/knowledge/holding_extractor.py)
- [ ] Not just "cites statute" but "holds that under § X, Y is required for Z"
- [ ] Classify each holding: rule statement, application, exception, limitation
- [ ] Store extracted holdings as searchable structured data
- [ ] Build heading/headnote system (AI equivalent of Westlaw KeyCite/Headnotes)
- [ ] Verify extracted holdings through citation verification chain
- [ ] 3-brain consensus required for each extracted holding

### Argument Graph (UPGRADE #2)
- [x] Argument graph engine built (src/knowledge/argument_graph.py)
- [ ] For each statute: build the full argument chain
- [ ] "Start with Case A (rule), supported by B, strengthened by C, defendant cites D"
- [ ] User gets an argument STRATEGY, not just a case list
- [ ] Store graph in Aurora PostgreSQL with recursive CTE queries
- [ ] Visualize argument graph in V0 frontend (nodes + edges)
- [ ] Red Team agent automatically finds counter-arguments from the graph

### Predictive Outcome Modeling (UPGRADE #3)
- [ ] Tag every cataloged case: plaintiff-win vs defendant-win
- [ ] Per statute + per jurisdiction: compute win probability
- [ ] "847 cases interpreting § 768.72 in S.D. Fla → 73% plaintiff success with expert proffer"
- [ ] Factor in: court, judge, year, practice area, evidence type
- [ ] Display win probability in case dashboard
- [ ] Update predictions as new cases are cataloged (continuous learning)

### Contradiction Detection Engine (ENHANCEMENT)
- [ ] When dual-brain disagrees on a holding: analyze WHY they disagree
- [ ] Catalog statutory ambiguities automatically
- [ ] Flag genuine conflicts of law (not just model errors)
- [ ] Create "ambiguity reports" — valuable for attorneys

### Cross-Jurisdiction Conflict Router (ENHANCEMENT)
- [ ] Meta-container above jurisdiction containers
- [ ] Handles choice-of-law analysis (contract signed in TX, breach in LA, suit in FED)
- [ ] Queries multiple containers simultaneously and reconciles
- [ ] Identifies which jurisdiction's law governs each issue

### Temporal Versioning (ENHANCEMENT)
- [ ] Maintain historical versions of statutes (not just current law)
- [ ] "Law as it existed on DATE" for retroactivity and SOL analysis
- [ ] Amendment timeline per statute with effective dates

### Confidence Decay (ENHANCEMENT)
- [ ] Model knowledge confidence decays over time since last corpus refresh
- [ ] Stale containers report lower confidence on recent issues
- [ ] Auto-trigger re-crawl when confidence drops below threshold

### Container-to-Container Citation Sharing (ENHANCEMENT)
- [ ] Federal case verified → broadcast to ALL state containers
- [ ] One container's verification benefits all others
- [ ] Reduces redundant CourtListener API calls across jurisdictions

---

## PHASE 2: MULTI-MODEL ARCHITECTURE [~60% COMPLETE]

- [x] 3-tier model router (Opus orchestrator + extended WDC + dual-brain)
- [x] Bedrock model mapping (real ARNs from aws bedrock list-foundation-models)
- [x] Auto-rotation via MODEL_OVERRIDE_{ROLE} env vars
- [x] Dual-brain per jurisdiction (Opus + Llama 4 Scout + Cohere Command-R+)
- [ ] Wire model_router into orchestrator (replace single-model invoke)
- [ ] Wire extended WDC panel (8 models scoring instead of 5)
- [ ] Wire dual-brain into jurisdiction container queries
- [ ] Benchmark: dual-brain consensus accuracy vs single-model
- [ ] Cost optimization: use Tier 3 models for non-legal tasks

---

## PHASE 3: DEPLOYMENT + BETA [REMAINING]

- [ ] Connect GitHub → Cloudflare Pages (user + admin)
- [ ] Create ECS Fargate service with ALB
- [ ] Alembic migration via ECS init container
- [ ] First real Bedrock API call end-to-end
- [ ] Start perpetual crawler (background ECS task)
- [ ] First beta user invited
- [ ] First real case processed through full pipeline
- [ ] Sentry DSN wired for production error tracking
- [ ] Promote dev → staging (WDC gate review)
- [ ] Promote staging → main (manual approval)

---

## PHASE 4: PRODUCTION HARDENING [NOT STARTED]

- [ ] SOC 2 Type II documentation
- [ ] EU AI Act Article 9/11 conformity docs
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Formal STRIDE threat model
- [ ] E&O insurance consideration
- [ ] Load testing + cost optimization
- [ ] Error Museum populated from beta feedback
- [ ] WDC calibration from real case outcomes

---

## HARD MANDATES (ALL PHASES)

1. No placeholders/filler/simulations/demo data — EVER (hook enforced)
2. No AI attribution in commits (@M:014)
3. Citation verification: external text only, never model memory
4. Deadline computation: conservative (earlier date when ambiguous)
5. Admin panel fully disconnected from user UI
6. DEV: Anthropic. PROD: Bedrock Core (best per agent class)
7. All CI quality gates enforced — no continue-on-error
8. All UI via V0 — no hand-written components
9. Dual-brain consensus required for legal holdings
12. Perpetual crawler runs until ALL case law cataloged
13. No hardcoded secrets — all via env vars / AWS Secrets Manager / Parameter Store
14. Deploy pipeline: Git → CI/CD → AWS (Bedrock backend) → Cloudflare (frontend/admin)
15. TODO.md and EXECUTION_JOURNAL.md updated after every QAD loop
16. No code deletion — append/refactor only
17. Persistent chat visible on ALL screens (consumer UI mandate)
18. 90% Galvanizer confidence gate — nothing filed below threshold

---

## METRICS

| Metric | Current | Target |
|--------|---------|--------|
| Python files | 55+ | — |
| Lines of code | 60,000+ | — |
| Tests passing | 33+ | 200+ |
| Jurisdictions | 57 | 57 (complete) |
| Practice sub-areas | 28 | 28 (complete) |
| Overlap rules | 7 | 50+ (all states) |
| Cases cataloged | 0 | 12,000,000+ |
| Statutes indexed | 0 | 100,000+ |
| Agents operational | 5 | 5 + 3 extended + 3 dual-brain |
| Real API calls | 0 | First call is #1 priority |
| Production readiness | ~25% | 100% |
