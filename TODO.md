# CYPHERGY — TODO
# Format: [ ] pending | [~] in-progress | [x] done | [!] blocked | [-] deferred
# Rule: ONE [~] task at a time. Finish before starting next.

---

## OPEN PRs (review before new work)

- [~] PR #2: Devin — 4 remaining agents (feature/remaining-agents)
      Action: WDC review, resolve conflicts with Phase 0 base_agent/lead_counsel/citation_chain
- [ ] PR #3: Session TODO (chore/session-todo) — merge after this file lands
- [-] PR #1: Copilot scaffold (draft) — evaluate or close

---

## P0 — IMMEDIATE

- [ ] WDC review Devin PR #2 — keep our Phase 0 code, merge only 4 new agent files
- [ ] V0: User-facing UI (cyphergy.ai)
      Clean like ChatGPT/Claude — conversational input, no marketing on app/mobile
      Marketing only on /pricing, /about pages
- [ ] V0: Master admin panel (FULLY SEPARATE from user UI)
      Analytics, connector management, system override, chat+coding agents, git+redeploy
      No source code visible from browser inspect, no jailbreak from user UI
- [ ] Commit 48 untracked prototype files (ciphergy/, agents/, core/, etc.) or .gitignore them
- [ ] FastAPI app entrypoint (src/api.py) with health check
- [ ] Wire Opus 4.6 as orchestrator managing all agents in dev

---

## P1 — FOUNDATION COMPLETE

- [ ] Bedrock provider adapter (swap Anthropic → Bedrock via LLM_PROVIDER env)
- [ ] Wire all 5 agents into orchestrator with full WDC debate loop
- [ ] Integration test: Lead Counsel → real Anthropic API → real response
- [ ] Integration test: Citation Verification Chain → real CourtListener lookup
- [ ] Merge Devin's agents after WDC review + write tests for each

---

## P2 — LEGAL KNOWLEDGE

- [ ] Verified Authority Registry (pgvector-backed)
- [ ] Jurisdiction Rules Engine (expand beyond 6 states)
- [ ] Case Knowledge Store schema (22 extraction sections)
- [ ] CourtListener MCP server
- [ ] US Code API integration

---

## P3 — JURISDICTION CONTAINERS (new architecture)

- [ ] Design: Each jurisdiction gets its own fine-tuned model container
      50 states + federal + territories, each learns from WDC debates
- [ ] Training pipeline: WDC transcripts → SageMaker fine-tuning → Bedrock deployment
- [ ] HuggingFace base models (LegalBERT or fine-tuned Llama) for jurisdiction-specific training
- [ ] Benchmark framework: measure per-jurisdiction accuracy vs general-purpose AI
- [ ] Linear integration for tracking training pipeline tasks

---

## P4 — PRODUCTION

- [ ] SOC 2 Type II documentation
- [ ] EU AI Act Article 9/11 conformity docs
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Formal STRIDE threat model
- [ ] Revenue model: bear case (15-25% conversion) as planning target
- [ ] Deploy to staging with feature flags OFF, progressive enable

---

## COMPLETED (2026-03-15 Session)

- [x] 4 V3.1 spec documents (Section 15, 16, E17, Medium Gaps) — 8,241 lines
- [x] WDC v3.1 re-score: 8.585/10 CERTIFIED
- [x] Phase 0: BaseAgent + LeadCounsel + Citation Chain + Deadline Calc + WDC Engine
- [x] 62 tests passing (33 new + 29 prototype)
- [x] Infrastructure: Dockerfile, docker-compose, CloudFormation, ECS, deploy script
- [x] CI/CD: GitHub Actions + Dependabot + weekly security scan
- [x] Security: 4-layer rate limiter, WAF, GUARDRAILS.yml, no-placeholders hook
- [x] Integrations: Sentry, Linear, .env.example (40 keys)
- [x] CLAUDE.md + Devin orchestration protocol
- [x] Devin tasked: 4 agents (PR #2 open)
- [x] Pushed 22,747 lines to GitHub

---

## HARD MANDATES

1. No placeholders/filler/simulations/demo data — EVER (hook enforced)
2. No AI attribution in commits (@M:014)
3. Citation verification: external text only, never model memory
4. Deadline computation: conservative (earlier date when ambiguous)
5. Admin panel fully disconnected from user UI
6. DEV: Anthropic (Opus 4.6 orchestrator). PROD: Bedrock Core (best per agent class)
7. All CI quality gates enforced — no continue-on-error
