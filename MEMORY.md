# Cyphergy Project Memory
**Owner:** Bo Pennington | bo@symio.ai
**Created:** 2026-03-15
**Repository:** https://github.com/OrionDevPartners/Cyphergy
**Base Directory:** /Users/bopennington/LOCAL ONLY /DEV-OPS/Cyphergy-Legal/

---

## Architecture Overview

### 5-Agent Legal Co-Counsel System
- **Lead Counsel** (30% weight): Strategic motion direction, case law synthesis, final review
- **Research Agent** (25% weight): Citation retrieval, CourtListener API integration, statute lookup
- **Drafting Agent** (15% weight): Motion composition, legal writing, formatting
- **Red Team** (20% weight): Adversarial review, opposing argument generation, weak point identification
- **Compliance Agent** (10% weight + VETO): HIPAA/GDPR/CCPA compliance, PII scrubbing, audit requirements

**Model:** All agents run **Claude Opus 4.6** (1M context) — no model tiering for legal domain (citation accuracy is non-negotiable)

**Validation:** WDC v2.0 (Weighted Debate Consensus) for all output validation

### Design Principles
1. **CPAA (Code-Provider Agnostic Architecture)**: All LLM providers, data sources, and services configured via environment variables — zero hardcoding
2. **Citation Verification Chain (CVC)**: Compound reliability architecture with external-retrieval hard constraint (Step 3 MUST read actual court opinion text, never model memory alone)
3. **Correlated Model Failure Protection**: Multi-agent consensus prevents systemic hallucination in legal citations

### Enhancements
- **E1-E12**: Winning features (feature parity with Westlaw/Lexis, real-time motion drafting, AI UX, etc.)
- **E13-E18**: WDC + Compass integration + verification chains + compliance frameworks

---

## Specification Status

| Document | Status | Location | Lines |
|----------|--------|----------|-------|
| CIPHERGY-FINAL-ROADMAP.md | ✓ Frozen | On disk | 679 |
| CIPHERGY-WINNING-EDGE-ENHANCEMENTS.md | ✓ Frozen | On disk | 783 |
| WDC-COMPASS-ANALYSIS.md | ✓ Frozen | On disk | 665 |
| WDC-V2-SPEC-REVIEW.md | ✓ Frozen | On disk | 577 |
| CIPHERGY_V3.1_SECTION14_ETHICAL_LEGAL_FRAMEWORK.md | ✓ Frozen | On disk | 415 |
| CIPHERGY_PRODUCT_SPEC_V2 | ✓ Frozen | On disk | Full spec |
| CIPHERGY_PRODUCT_SPEC_V3_DELTA | ✓ Frozen | On disk | V3 deltas |
| Section 15: Data Privacy & Security | ✓ Drafted | Transcript only | ~1,100 |
| Section 16: Testing Strategy | ✓ Drafted | Transcript only | ~1,100 |
| E17: Verification Chains | ✓ Drafted | Transcript only | ~1,100 |
| Medium Gaps (Batch, Offline, Onboarding, Revenue) | ✓ Drafted | Transcript only | ~2,000 |

**Spec Status:** V3.1 Composite Score: **8.585 / 10.0** — **CERTIFIED**
**Specification Frozen:** 2026-03-15

**Drafted Content Locations:**
- Section 15 Data Privacy: `/private/tmp/claude-501/-Users-bopennington/tasks/ab698c4225e40747a.output`
- Section 16 Testing: `/private/tmp/claude-501/-Users-bopennington/tasks/a0a3a040c1828d066.output`
- E17 Verification Chains: `/private/tmp/claude-501/-Users-bopennington/tasks/a40f5df04ebd1cd0b.output`
- Medium Gaps: `/private/tmp/claude-501/-Users-bopennington/tasks/ac273ffa9e38d75a0.output`

---

## Phase Implementation Plan

### Phase 0 (Current — Code Infrastructure)
**Duration:** 2 weeks
**Deliverable:** Runnable CI/CD, single-agent API, core data models
**Priority Order:**

1. **Priority 1: Single Agent (Lead Counsel) → Real API Call**
   - [ ] Load LLM provider from env (`LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `LLM_MODEL`)
   - [ ] Create `MotionDraftingRequest` Pydantic model
   - [ ] Call Claude Opus 4.6 for single motion (no external APIs yet)
   - [ ] Return structured output with citations placeholder
   - [ ] Test: 1 unit test for LLM call

2. **Priority 2: Citation Verification Chain (Hard Constraint)**
   - [ ] Create 5-step CVC with external retrieval requirement
   - [ ] Step 3: Read actual CourtListener opinion text (NO model memory)
   - [ ] Implement correlated failure detection
   - [ ] Test: 3 adversarial cases with conflicting citations

3. **Priority 3: Deadline Calculator (17 Tests)**
   - [ ] Parse all 50 state civil procedure rules + Federal Rules
   - [ ] Compute motion deadlines from case filing date
   - [ ] Implement grace period logic (weekends, holidays, e-filing cutoffs)
   - [ ] Test: 17 edge cases (cross-year, leap days, 11:59pm filing, etc.)

**Definition of Done:** GitHub CI/CD green, 100% test coverage on Phase 0 modules, WDC score ≥ 8.5 on spec validation.

### Phase 1 (Database + Multi-Agent + Compliance)
- Database: PostgreSQL for document storage, citation cache, audit logs
- Multi-agent: Full 5-agent consensus with WDC scoring
- Compliance: HIPAA/GDPR/CCPA with cryptographic deletion, per-tenant KMS

### Phase 2 (User Experience + Features)
- Batch document intake
- Offline courtroom mode
- 5-minute time-to-value onboarding UX

### Phase 3 (Monetization + Scale)
- Year 1 revenue model: $784K (low), $2.28M ARR (high-case scenario)
- SaaS pricing: $3.99/motion (consumer), $499/month (firm)

---

## Key Decisions & Constraints

### Architectural Hard Constraints
1. **Citation Verification Step 3 External Retrieval**: Must read actual opinion text from CourtListener/court databases; never rely on model memory for legal citations
2. **All-Opus Model Selection**: No cost optimization tiering for legal outputs (ChatGPT/Claude 3.5 Sonnet for legal analysis = too risky)
3. **CPAA Compliance**: Every secret, endpoint, model name, and database URL goes through env vars — zero hardcoding

### Revenue Planning
- Use 15-25% conversion as base case (NOT 40%)
- Per-motion cost: $4.21 (OpenAI + attorney review) vs. $2K-5K (traditional attorney)
- Year 1 targets: 500 active users (firms), 2-5 motions/user/month

### Legal Domain Specifics
- Statute of Limitations: 13-17 state variations per case type
- Motion Deadline Calculation: 50-state civil procedure rules = computational nightmare
- Citation Chains: CourtListener → US Code → CFR → case law (multi-layer dependency graph)

---

## Development Workflow

### Before Starting Each Session
1. Read canonical memory: `/Users/bopennington/LOCAL ONLY /DEV-OPS/MEMORY.md`
2. Read this project memory: `MEMORY.md`
3. Load environment: `source .env` (development mode)

### Commit Philosophy
- **NO AI attribution** — ever ("Co-Authored-By", "Generated by", etc.)
- All work is user's work (Bo Pennington)
- Clear commit messages: `fix: deadline calculation for NY SOL` not `AI fixed deadline`
- Link to spec/design docs in long-form commit bodies

### Code Review Standards
- Citation accuracy = must have external retrieval verification
- WDC score ≥ 8.5 on all legal outputs
- 100% test coverage on citation/deadline code
- Zero hardcoded secrets/endpoints

---

## External Integrations

### APIs (Phase 1+)
- **CourtListener**: Case law retrieval (free + paid tiers)
- **US Code API**: Statutory citations
- **CFR (Federal Register)**: Regulatory citations
- **Westlaw/Lexis**: (if partnerships enabled; currently using CourtListener)

### Compliance Frameworks
- **HIPAA**: Protected Health Information (PHI) scrubbing for medical malpractice cases
- **GDPR**: EU client data residency + cryptographic deletion
- **CCPA**: California consumer data privacy
- **CFR 28 § 1.1 et seq.**: US legal citation standards

### Monitoring
- Optional: Datadog APM, Sentry error tracking, custom telemetry

---

## Testing Strategy (from Section 16)

### 6-Layer Test Coverage
1. **Unit Tests** (Deadlines, Citations, Elements): 50+ tests
2. **Integration Tests** (CourtListener, US Code): 30+ tests
3. **Adversarial Tests** (Anti-hallucination): 20+ tests
4. **E2E Tests** (Full motion drafting): 10+ cases
5. **WDC Validation**: Consensus scoring ≥ 8.5
6. **Regression Tests**: Post-deployment safety checks

### Critical Test Cases
- Motion deadline for case filed on 2-29 (leap year edge case)
- Statute of Limitations across state lines
- Citation conflict resolution (two agents cite opposing precedent)
- PII scrubbing (medical records in facts section)
- HIPAA/GDPR/CCPA compliance audit

---

## Security Checklist

- [x] .gitignore excludes .env, *.docx, sensitive directories
- [x] .env.example has placeholder values only
- [x] pyproject.toml has zero secrets
- [x] CPAA: LLM provider configurable via `LLM_PROVIDER` env var
- [x] All API keys in environment variables only
- [ ] Database password rotation (Phase 1)
- [ ] Per-tenant KMS (Phase 1)
- [ ] Cryptographic deletion policy (Phase 1)
- [ ] HIPAA audit log (Phase 1)

---

## Contacts & Escalation
- **Owner:** Bo Pennington (bo@symio.ai)
- **GitHub Org:** OrionDevPartners
- **Legal Review:** (TBD Phase 1)
- **Compliance Officer:** (TBD Phase 1)

---

## Glossary

| Term | Definition |
|------|-----------|
| **CPAA** | Code-Provider Agnostic Architecture — providers/services via env vars, zero hardcoding |
| **CVC** | Citation Verification Chain — 5-step external retrieval + consensus validation |
| **WDC** | Weighted Debate Consensus — multi-agent scoring (0-10) for output quality |
| **PHI** | Protected Health Information (HIPAA category) |
| **PII** | Personally Identifiable Information (GDPR/CCPA category) |
| **CFR** | Code of Federal Regulations |
| **SOL** | Statute of Limitations |
| **Motion** | Legal document filed in court (e.g., "Motion to Dismiss") |
| **Lead Counsel** | Lead agent (30% weight) — strategic direction |

---

**Last Updated:** 2026-03-15
**Next Review:** After Phase 0 completion (2 weeks)
