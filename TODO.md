# CYPHERGY — FULL PRODUCTION ROADMAP (A to Z)
# Format: [ ] pending | [~] in-progress | [x] done | [!] blocked | [-] deferred
# Rule: ONE [~] task at a time. Finish before starting next.
# Source: CIPHERGY-FINAL-ROADMAP.md (8 phases) + V3.1 spec additions
# Last Updated: 2026-03-16

---

## PHASE 0: FOUNDATION
**Goal:** 5-agent architecture, WDC engine, core plumbing

### 0.1 Agent Architecture
- [x] 0.1.1 BaseAgent class with Anthropic API integration (base_agent.py — 419 lines)
- [x] 0.1.2 AgentRole enum, AgentConfig, AgentResponse, WDCScore models
- [x] 0.1.3 Lead Counsel agent with classify_task + aggregate_responses (lead_counsel.py — 362 lines)
- [~] 0.1.4 Research Counsel agent (Devin PR #2 — WDC review pending)
- [~] 0.1.5 Drafting Counsel agent (Devin PR #2 — WDC review pending)
- [~] 0.1.6 Red Team agent (Devin PR #2 — WDC review pending)
- [~] 0.1.7 Compliance Counsel agent with VETO power (Devin PR #2 — WDC review pending)
- [ ] 0.1.8 Wire Opus 4.6 as orchestrator managing all 5 agents in dev

### 0.2 Agent Communication
- [x] 0.2.1 Shared blackboard (dict) for case state
- [x] 0.2.2 Private scratchpads per agent
- [x] 0.2.3 Message history for multi-turn conversations
- [ ] 0.2.4 Inter-agent structured JSON messaging protocol
- [ ] 0.2.5 Agent routing logic (Lead Counsel → fan-out → fan-in)

### 0.3 WDC v2.0 Debate Engine
- [x] 0.3.1 WDCEngine class with score() method (wdc.py — 356 lines)
- [x] 0.3.2 WDCVerdict enum (CERTIFIED, CERTIFIED_WITH_NOTES, REVISION_REQUIRED, REJECTED, VETOED)
- [x] 0.3.3 Compliance VETO logic (overrides any composite score)
- [x] 0.3.4 16 WDC tests passing
- [ ] 0.3.5 run_debate() — async full debate cycle with all 5 agents
- [ ] 0.3.6 Revision loop (if REVISION_REQUIRED, re-draft and re-score up to 3 cycles)

### 0.4 Verification Chain
- [x] 0.4.1 CitationVerifier 5-step pipeline (citation_chain.py — 1,314 lines)
- [x] 0.4.2 External-retrieval hard constraint (Step 3 — model memory NEVER sufficient)
- [x] 0.4.3 CourtListener API integration (search, fetch opinion text)
- [x] 0.4.4 Batch verification with asyncio.gather
- [ ] 0.4.5 Integration test against real CourtListener API

### 0.5 Deadline Calculator
- [x] 0.5.1 DeadlineCalculator with 6 jurisdictions (deadline_calc.py — 478 lines)
- [x] 0.5.2 17 deadline tests — all passing
- [x] 0.5.3 Conservative computation (earlier date when ambiguous)
- [x] 0.5.4 Holiday engine with algorithmic computation
- [ ] 0.5.5 Expand to 10+ states (IL, GA, OH, PA, VA)
- [ ] 0.5.6 Court-specific local rule overrides

### 0.6 Configuration & Settings
- [x] 0.6.1 CPAA-compliant Settings (pydantic-settings, all from env)
- [x] 0.6.2 .env.example with 40 integration keys
- [x] 0.6.3 External retrieval hard constraint validator
- [ ] 0.6.4 Bedrock provider adapter (LLM_PROVIDER=bedrock for production)

### 0.7 API & App Entrypoint
- [ ] 0.7.1 FastAPI app (src/api.py) with /health endpoint
- [ ] 0.7.2 POST /api/v1/chat — Lead Counsel conversational endpoint
- [ ] 0.7.3 POST /api/v1/classify — task classification endpoint
- [ ] 0.7.4 POST /api/v1/verify-citation — citation verification endpoint
- [ ] 0.7.5 POST /api/v1/compute-deadline — deadline calculator endpoint
- [ ] 0.7.6 Wire security middleware (CORS, headers, request ID)
- [ ] 0.7.7 Wire rate limiter (4-layer)

### 0.8 Prototype Reconciliation
- [ ] 0.8.1 Audit 48 untracked prototype files (ciphergy/, agents/, core/, etc.)
- [ ] 0.8.2 Decide: commit (archive alongside src/) or .gitignore
- [ ] 0.8.3 Migrate any useful prototype code into src/ structure

---

## PHASE 1: AGENT CORE
**Goal:** All 5 agents wired with full debate consensus

- [ ] 1.1 Build full orchestration loop: user input → Lead Counsel classify → fan-out → WDC debate → deliver
- [ ] 1.2 Agent system prompts: wire Amendment 1.0 directives into each agent's behavioral protocol
- [ ] 1.3 Multi-turn conversation support across all agents
- [ ] 1.4 Agent state persistence (Redis working memory + Postgres episodic)
- [ ] 1.5 Checkpoint/rollback system (LangGraph-style state snapshots)
- [ ] 1.6 E13: What-If Strategy Branching (fork case state, model multiple paths)
- [ ] 1.7 Integration tests: full 5-agent debate on a test case scenario
- [ ] 1.8 Benchmark: measure response time, token usage, cost per debate cycle

---

## PHASE 2: LEGAL KNOWLEDGE ENGINE
**Goal:** Verified citations, jurisdiction rules, anti-hallucination

- [ ] 2.1 Verified Authority Registry (VAR) — pgvector-backed citation database
- [ ] 2.2 CourtListener MCP server (E16)
- [ ] 2.3 US Code API connector (uscode.house.gov XML)
- [ ] 2.4 eCFR API connector (ecfr.gov)
- [ ] 2.5 Google Scholar legal search (backup verification)
- [ ] 2.6 State statute connectors — top 10 states
- [ ] 2.7 Jurisdiction Rules Engine — structured rules per jurisdiction
- [ ] 2.8 Citation recheck pipeline (30-day currency check)
- [ ] 2.9 E9: Real-Time Case Law Monitoring (CourtListener webhooks)
- [ ] 2.10 E14: Outcome-Based Learning Engine (track case outcomes → improve recommendations)

---

## PHASE 3: CASE MANAGEMENT ENGINE
**Goal:** Full case lifecycle tracking

- [ ] 3.1 Case Knowledge Store — per-matter 22-section structured storage
- [ ] 3.2 Case state machine — tracks litigation phase, transitions, active deadlines
- [ ] 3.3 Deadline engine — proactive warnings, calendar integration, tiered reminders (14/7/3/1 day)
- [ ] 3.4 Evidence inventory — upload, classification, chain of custody, authentication
- [ ] 3.5 Extraction automation — auto-generate 22-section extraction on demand
- [ ] 3.6 Document processing pipeline — complaint analyzer, motion analyzer, contract reviewer
- [ ] 3.7 Claims/defenses tracker — elements mapping, evidence linking, viability scoring
- [ ] 3.8 E1: Evidence Weaponization Engine (element-evidence matrix, discovery sequencing)
- [ ] 3.9 E6: Opposing Party Vulnerability Scanner (public records deep scan)
- [ ] 3.10 E7: Procedural Trap Detector (monitor opposing party for violations)
- [ ] 3.11 Batch Document Intake pipeline (14-category classification, OCR, priority routing)

---

## PHASE 4: DOCUMENT GENERATION
**Goal:** Court-ready .docx/.pdf filing production

- [ ] 4.1 docxtpl rendering engine — court-formatted documents
- [ ] 4.2 WeasyPrint PDF generation — memos, research summaries
- [ ] 4.3 Court-specific format profiles — federal + state systems + local rules
- [ ] 4.4 Template library — motions, pleadings, discovery, correspondence per jurisdiction
- [ ] 4.5 Watermark/marking system — DRAFT/WORK PRODUCT/CONFIDENTIAL headers
- [ ] 4.6 File naming convention enforcement
- [ ] 4.7 E-filing format validation (PDF/A, font restrictions)
- [ ] 4.8 Exhibit preparation — Bates numbering, exhibit tabs, exhibit lists
- [ ] 4.9 Document revision tracking with diff view
- [ ] 4.10 E8: Case Narrative Engine (theory of case, visual timeline, jury instructions)
- [ ] 4.11 E10: Pro Se Credibility Optimizer (professional formatting, filing quality score)

---

## PHASE 5: INTEGRATIONS & CONNECTORS
**Goal:** Wire external services via MCP protocol

- [ ] 5.1 Google Drive connector — matter file organization, document storage
- [ ] 5.2 Google Calendar — deadline events with tiered reminders
- [ ] 5.3 Gmail connector — draft composition, prior communication search
- [ ] 5.4 Asana connector — litigation project management
- [ ] 5.5 PACER/CM-ECF connector — federal court docket access
- [ ] 5.6 State court portal connectors — e-filing status, docket search
- [ ] 5.7 E16: Build 10 custom legal MCP servers (open-source ecosystem play)
- [ ] 5.8 Integration testing suite for all connectors
- [ ] 5.9 Slack connector — status updates, context retrieval
- [ ] 5.10 DocuSign — e-signatures

---

## PHASE 6: PRO SE FEATURES
**Goal:** Features that level the playing field for self-represented litigants

- [ ] 6.1 Plain Language Translator — legal jargon ↔ plain English
- [ ] 6.2 Filing Checklist Generator — step-by-step per court
- [ ] 6.3 E4: Judge Profile Engine — CourtListener data, ruling patterns, preferences
- [ ] 6.4 Fee Waiver Assistant — IFP application guidance + form generation
- [ ] 6.5 Legal Aid Eligibility Screener — LSC, pro bono panels, law school clinics
- [ ] 6.6 Courtroom Procedure Coach — hearing expectations, etiquette, objection basics
- [ ] 6.7 Service of Process Guide — per-jurisdiction with approved methods
- [ ] 6.8 Court Form Finder — mandatory forms with pre-fill
- [ ] 6.9 Offline Courtroom Mode — pre-hearing package, PDF export, mobile cache
- [ ] 6.10 E2: Settlement Pressure Engine (cost-of-litigation modeling, demand letters)
- [ ] 6.11 E3: Motion Practice Warfare (offensive sequencing, RFA warfare, SJ packages)
- [ ] 6.12 E5: Damages Maximization Engine (taxonomy, claim stacking, interest calc)
- [ ] 6.13 E12: Appeal Preservation Engine (issue tracker, objection generator)
- [ ] 6.14 E15: Opposing Counsel Profiling (litigation history, exploitable patterns)

---

## PHASE 7: FRONTEND & UX
**Goal:** User-facing app + admin panel

### User-Facing UI (cyphergy.ai)
- [ ] 7.1 V0: Design conversational interface (clean like ChatGPT — input box, nothing else)
- [ ] 7.2 V0: Case dashboard (claims, deadlines, evidence inventory, confidence scores)
- [ ] 7.3 V0: Document viewer/editor with confidence flags
- [ ] 7.4 V0: Deadline calendar with color-coded urgency
- [ ] 7.5 Expo React Native mobile app — zero marketing, clean, ready to go
- [ ] 7.6 Onboarding UX — 5-step flow, first value in 5 minutes
- [ ] 7.7 14-day reverse trial (Pro features → downgrade to Free)
- [ ] 7.8 WCAG 2.1 AA accessibility compliance
- [ ] 7.9 SSE streaming for real-time agent output
- [ ] 7.10 E18: Real-Time Cost Transparency dashboard

### Master Admin Panel (FULLY SEPARATE)
- [ ] 7.11 V0: Full analytics dashboard (users, cases, agents, costs, accuracy)
- [ ] 7.12 V0: Connector plug-in management (add/remove/configure integrations)
- [ ] 7.13 V0: System-wide override controls (feature flags, model routing, thresholds)
- [ ] 7.14 V0: Built-in chat with coding agents (git + redeploy from panel)
- [ ] 7.15 Separate deployment — no shared code with user UI
- [ ] 7.16 No source code visible from browser inspect
- [ ] 7.17 Admin auth: separate identity provider, MFA required

---

## PHASE 8: HARDENING & PRODUCTION
**Goal:** Battle-tested, compliant, deployed

### Testing
- [ ] 8.1 E2E tests with 10 anonymized real case scenarios
- [ ] 8.2 Citation accuracy audit — verify 100% of citations in test outputs
- [ ] 8.3 Deadline computation testing — verify against known court calendars
- [ ] 8.4 Red Team stress test — Agent 4 attacks every output type
- [ ] 8.5 Jurisdictional coverage testing — top 10 states + federal
- [ ] 8.6 WDC calibration — tune debate weights/thresholds from test metrics
- [ ] 8.7 Load testing + cost optimization
- [ ] 8.8 Error Museum — document every bug with root cause and regression test

### Compliance & Security
- [ ] 8.9 SOC 2 Type II audit preparation
- [ ] 8.10 EU AI Act Article 9/11 conformity documentation
- [ ] 8.11 Formal STRIDE/PASTA threat model
- [ ] 8.12 Penetration testing (annual schedule)
- [ ] 8.13 E&O insurance consideration
- [ ] 8.14 State bar AI guidelines compliance tracker

### Deployment
- [ ] 8.15 Deploy to staging (ECS Fargate) with all feature flags OFF
- [ ] 8.16 Smoke test: full case lifecycle on staging
- [ ] 8.17 Progressive feature flag rollout (Phase 1 features first)
- [ ] 8.18 Production deployment — cyphergy.ai live
- [ ] 8.19 Monitoring: Sentry, CloudWatch, cost alerts
- [ ] 8.20 E11: Compliance Monitoring Dashboard (court order tracker, opposing party compliance)

### Go-to-Market
- [ ] 8.21 Pricing: Free ($0) / Pro ($29) / Team ($49/user) / Enterprise (custom)
- [ ] 8.22 Revenue model: bear case (15-25% conversion) as planning target
- [ ] 8.23 Content marketing + legal forum SEO
- [ ] 8.24 Legal aid organization partnerships
- [ ] 8.25 Beta invite program (500 free users)

---

## PHASE 9: JURISDICTION CONTAINERS (Future — Post-Launch)
**Goal:** Per-jurisdiction fine-tuned models that outperform general AI

- [ ] 9.1 Architecture: each jurisdiction = own container with fine-tuned model
- [ ] 9.2 Training pipeline: WDC debate transcripts → SageMaker → Bedrock deployment
- [ ] 9.3 HuggingFace base models (LegalBERT / fine-tuned Llama)
- [ ] 9.4 First container: Louisiana (home jurisdiction)
- [ ] 9.5 Second container: Federal
- [ ] 9.6 Benchmark framework: per-jurisdiction accuracy vs general-purpose AI
- [ ] 9.7 Scale to 50 states + territories
- [ ] 9.8 E14 integration: outcome data feeds training loop

---

## INFRASTRUCTURE (Cross-Phase)

### Already Done
- [x] Dockerfile (multi-stage, non-root, health check)
- [x] docker-compose.yml (app + Postgres 16/pgvector + Redis 7)
- [x] CloudFormation (ECS Fargate, ALB, S3, ECR, IAM)
- [x] ECS task definition with Secrets Manager
- [x] Deploy script (build → ECR → ECS rolling update)
- [x] GitHub Actions CI (lint, test, security scan)
- [x] Weekly security scan + Dependabot
- [x] 4-layer rate limiter (IP/user/tenant/global circuit breaker)
- [x] Security middleware (HSTS, CSP, CORS, request ID audit)
- [x] Cloudflare WAF rules (10 rules + managed rulesets)
- [x] GUARDRAILS.yml + no-placeholders hook
- [x] Sentry + Linear integrations
- [x] CLAUDE.md + Devin orchestration protocol

### Remaining
- [ ] Wire Sentry DSN in production
- [ ] Wire Linear team ID for project tracking
- [ ] Set up AWS Secrets Manager entries for production
- [ ] Configure Cloudflare DNS for cyphergy.ai
- [ ] SSL certificate via Cloudflare
- [ ] Set up monitoring dashboards (CloudWatch)
- [ ] Set up cost alerts (AWS Budgets)

---

## HARD MANDATES (Apply to ALL phases)

1. No placeholders/filler/simulations/demo data — EVER (hook enforced)
2. No AI attribution in commits (@M:014)
3. Citation verification: external text only, never model memory
4. Deadline computation: conservative (earlier date when ambiguous)
5. Admin panel fully disconnected from user UI
6. DEV: Anthropic (Opus 4.6 orchestrator). PROD: Bedrock Core (best per agent class)
7. All CI quality gates enforced — no continue-on-error
8. PII never in logs, file names, or task titles

---

## METRICS

| Metric | Current | Target |
|--------|---------|--------|
| Python files | 83 | — |
| Lines of code | 22,316 | — |
| Tests passing | 62 | 200+ |
| WDC spec score | 8.585 | 8.5+ maintained |
| Citation accuracy | untested | 99.9% |
| Deadline accuracy | 17/17 tests | 100% |
| Jurisdictions | 6 | 50+ states + federal |
| API endpoints | 0 | 5+ (Phase 0.7) |
| Agents operational | 1 (Lead) | 5 (full WDC) |
| Production readiness | ~15% | 100% |
