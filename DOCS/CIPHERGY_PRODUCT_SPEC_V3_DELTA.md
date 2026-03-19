# CIPHERGY PRODUCT SPEC — V3 DELTA

## Changes from V2.0 → V3.0
## March 15, 2026

**Source:** Claude Code WDC-COMPASS-ANALYSIS.md (5-agent panel review scoring 7.725/10)

This document captures only the CHANGES. V2.0 remains the base. Apply these corrections and additions on top.

---

## CORRECTION 1: MODEL TIERING — LEGAL DOMAIN EXEMPT

**V2 said:** Route simple tasks → Haiku, standard → Sonnet, complex reasoning → Opus via LiteLLM.

**V3 says:** Model tiering applies to Construction Pack, Business Ops Pack, and general platform operations. **The Legal Litigation Pack is ALL-OPUS, no exceptions.** In legal, there are no "simple tasks." A statute lookup that uses a cheaper model might miss a recent amendment. A deadline computation on a lighter model might miscalculate holidays. Citation verification on anything less than maximum reasoning = malpractice.

**Implementation:** The Agent Pack YAML manifest includes a `model_override` field:
```yaml
pack:
  name: "Legal Litigation Pack"
  model_policy: "all_opus"  # overrides platform-level model tiering
  model_override: "claude-opus-4-6"  # every agent, every task
```

Other packs use the default tiered routing:
```yaml
pack:
  name: "Construction Management Pack"
  model_policy: "tiered"  # Haiku/Sonnet/Opus per task complexity
```

---

## CORRECTION 2: WESTLAW/LEXISNEXIS — REMOVE FROM V1 INTEGRATIONS

**V2 said:** Westlaw API and LexisNexis APIs as priority integrations.

**V3 says:** These are $50K+/year enterprise contracts. At $29/month, economically impossible for V1. Move to Enterprise tier only (custom pricing).

**V1 Legal Research Stack (free/low-cost):**
- CourtListener / RECAP (free) — 12M+ opinions, judge profiles
- Google Scholar Legal (free) — Case law search
- US Code via govinfo.gov (free) — Federal statutes
- eCFR via ecfr.gov API (free) — Federal regulations
- PACER Case Locator ($0.10/page) — Federal court filings
- State legislature APIs (free) — Bill tracking, statute updates
- SEC EDGAR (free) — Corporate filings

**Enterprise-only (custom pricing):**
- Westlaw API (Thomson Reuters)
- LexisNexis APIs
- Bloomberg Law API

---

## ADDITION: 6 NEW ENHANCEMENTS (E13-E18)

Total enhancement count: 18 (E1-E12 from Winning Edge + E13-E18 from WDC integration)

### E13: What-If Strategy Branching

Fork case state at decision points. Model multiple litigation paths simultaneously. Compare on: win probability, cost, time, risk exposure, settlement leverage. Present branches to user with recommendation.

**Example:** "Should we file MSJ?" → System models three branches (file MSJ, skip to trial, file partial MSJ) with probability trees, cost estimates, and timeline impacts. This is what senior litigators do mentally. Ciphergy does it explicitly with auditable reasoning.

**Architecture:** LangGraph-style checkpointing. Fork state → run each branch with all 5 agents → aggregate results → present comparison matrix.

**Agent owners:** Lead Counsel (orchestrates) + Red Team (stress tests each branch) + Compliance (verifies deadlines per path)

### E14: Outcome-Based Learning Engine

Track actual case outcomes to improve future recommendations. Every resolved case feeds back: jurisdiction, judge, case type, claims filed, motions filed (and results), discovery strategy, settlement/trial outcome, system performance metrics (citations verified, deadlines met).

**Over time creates:** Judge-specific win rates per motion type, jurisdiction-specific strategy effectiveness, evidence type → outcome correlations, optimal settlement timing insights, citation reliability scores.

**Privacy:** Outcome data is anonymized and aggregated. No PII in the learning corpus. Users opt-in to contribute.

**Agent owners:** Compliance Counsel (tracks data) + Lead Counsel (ingests for future strategy)

### E15: Opposing Counsel Profiling

Profile the opposing party's *lawyer*, not just the party. Data from public sources: CourtListener (prior cases, win/loss records), state bar (discipline history, practice areas), firm website (bio, specialties), PACER (motion practice style, typical arguments).

**Output:** Motion practice style, trial history, exploitable patterns (e.g., "uses boilerplate discovery objections → motion to compel citing specific deficiencies"), settlement timing patterns, risk assessment.

**Agent owners:** Research Counsel (builds profile) + Red Team (incorporates into adversarial modeling)

### E16: MCP Legal Tool Ecosystem

Build 10 Ciphergy-specific MCP servers for legal tools that don't exist in the 1,200+ MCP ecosystem:

| MCP Server | Function |
|------------|----------|
| `ciphergy-courtlistener` | Case law search, opinion retrieval, docket access |
| `ciphergy-uscode` | Federal statute lookup with section-level search |
| `ciphergy-ecfr` | Federal regulation lookup |
| `ciphergy-pacer` | Federal court docket search and filing retrieval |
| `ciphergy-state-sos` | Business entity search (Secretary of State) |
| `ciphergy-deadline-calc` | Jurisdiction-aware deadline computation |
| `ciphergy-citation-verify` | 5-step citation verification pipeline |
| `ciphergy-judge-analytics` | Judge profile and ruling pattern analysis |
| `ciphergy-var` | Verified Authority Registry CRUD |
| `ciphergy-form-finder` | Court-specific form lookup and pre-fill |

**Strategic play:** Open-source these servers. Any MCP-compatible platform can use them. Ciphergy becomes the legal MCP authority. Community adoption → ecosystem lock-in → developer goodwill.

### E17: Compound Reliability Safeguard

At 85% per-action accuracy, a 10-step workflow succeeds only 20% of the time. For legal, one error = case dismissal.

**Solution: Verification Chains, Not Action Chains**

Every agent output passes through at least one other agent before advancing. Citation verification is a SEPARATE step from citation generation. Drafting uses ONLY verified inputs. Red Team catches errors that passed verification. Compliance catches procedural errors Red Team missed.

**The math:** With verification at each step, effective per-step accuracy = 0.85 + (0.15 × 0.85) = 97.75%. Compound over 4 steps: 91.2% success. With 5-agent cross-checking: approaches 99.5% per step → 95.1% over 10 steps. This is the difference between a demo and a product.

### E18: Real-Time Cost Transparency

Dashboard showing: current month budget vs spend, top cost drivers by agent and task type, cost-per-deliverable breakdown (e.g., "Motion to Compel: $4.80 vs attorney: $2,000-5,000"), projected month-end spend, and savings vs traditional legal services.

**Agent owner:** System-level. Compliance Counsel monitors budget enforcement.

---

## ADDITION: DRAFTING COUNSEL ENHANCEMENTS (from WDC Agent 3)

V2 mentioned docxtpl + WeasyPrint but Claude Code identified four missing capabilities:

1. **Court-specific template registry** — Structured template catalog per court, per jurisdiction. Every court has different caption formats, margin requirements, font requirements, page limits, certificate of service format, and local rule compliance statements.

2. **Track changes / revision history** — When WDC debate sends a draft back for revision, the user sees what changed and why. Critical for trust and learning.

3. **E-filing format validation** — Many courts require specific PDF standards (PDF/A, no embedded fonts, specific page sizes). Validate before user files.

4. **Exhibit preparation** — Bates numbering, exhibit tabs, exhibit lists. These are drafting tasks no competitor addresses.

---

## ADDITION: RED TEAM ENHANCEMENTS (from WDC Agent 4)

V2 described Red Team generically. Claude Code identified three specific capabilities to add:

1. **Counter-argument registry** — Persistent database of every counter-argument generated across all filings. If the same weakness appears in multiple filings, it's flagged as a systemic case weakness, not a one-off issue.

2. **Judge-specific adversarial modeling** — Red Team doesn't argue generically. It argues as opposing counsel would argue **before this specific judge**, using judicial analytics data. Different judges respond to different argument structures.

3. **Settlement-context Red Team** — Before any settlement negotiation, Red Team models opposing party's BATNA (best alternative to negotiated agreement), evaluates likely counter-offers, and identifies pressure points for negotiation strategy.

---

## ADDITION: COMPLIANCE COUNSEL — OUTCOME TRACKING

V2 described compliance monitoring but not outcome tracking. Claude Code identified that Gartner's prediction (40%+ of agentic AI projects scrapped for "unclear value") means Ciphergy must prove value through measurable outcomes.

**Compliance Counsel tracks:**
- Cases where system was used → outcome (won/lost/settled/dismissed)
- Settlement amounts achieved vs initial demand
- Deadlines met vs missed
- Motions filed → granted/denied rates
- Citations used → verified/unverified/challenged rates

This creates the feedback loop that makes E14 (Outcome-Based Learning) possible.

---

## REVISED 4-LAYER ARCHITECTURE

Claude Code's merge strategy is the correct framework:

```
LAYER 4 (TOP):   WINNING EDGE ENHANCEMENTS (E1-E18)
                  ↑ What wins cases and forces settlements

LAYER 3:         CIPHERGY ROADMAP (8 phases, 5 agents, WDC v2.0)
                  ↑ Legal domain intelligence and agent architecture

LAYER 2:         PRODUCT SPEC V2/V3 (SaaS architecture, market, pricing)
                  ↑ Product infrastructure, business model, GTM

LAYER 1 (BASE):  REPO + Amendment 1.0 + Extraction Prompt
                  ↑ Existing code, protocols, behavioral guardrails
```

---

## REVISED COMPLETE SYSTEM (V3)

```
CIPHERGY V3: MULTI-AGENTIC AI ORCHESTRATION PLATFORM

INFRASTRUCTURE:
├── React/Vite frontend (Cloudflare Pages)
├── FastAPI backend (AWS ECS Fargate)
├── Postgres + pgvector + Redis (Neon → Aurora)
├── MCP-first integrations (10 custom legal MCP servers + 1,200+ ecosystem)
├── SSE streaming + WebSocket
├── Multi-tenant (RLS + RBAC + SSO)
├── Freemium pricing ($0 / $29 / $49 / custom)
├── Compound reliability safeguards (E17)
└── Real-time cost transparency (E18)

LEGAL AGENTS (All Opus 4.6 — no model tiering):
├── Agent 1: Lead Counsel (30%) — Strategy + user interface + filing management
├── Agent 2: Research Counsel (25%) — Legal research + citation verification + opposing counsel profiling
├── Agent 3: Drafting Counsel (15%) — Document generation + formatting + exhibit preparation
├── Agent 4: Adversarial Counsel (20%) — Red team + judge-specific modeling + settlement Red Team
├── Agent 5: Compliance Counsel (10% + VETO) — Deadlines + procedures + outcome tracking
└── WDC v2.0: 5-agent weighted debate with Compliance veto

WINNING EDGE (18 Enhancements):
├── E1:  Evidence Weaponization Engine
├── E2:  Settlement Pressure Engine
├── E3:  Motion Practice Warfare
├── E4:  Judicial Analytics Engine
├── E5:  Damages Maximization Engine
├── E6:  Opposing Party Scanner
├── E7:  Procedural Trap Detector
├── E8:  Case Narrative Engine
├── E9:  Real-Time Case Law Monitoring
├── E10: Pro Se Credibility Optimizer
├── E11: Compliance Monitoring Dashboard
├── E12: Appeal Preservation Engine
├── E13: What-If Strategy Branching [NEW in V3]
├── E14: Outcome-Based Learning Engine [NEW in V3]
├── E15: Opposing Counsel Profiling [NEW in V3]
├── E16: MCP Legal Tool Ecosystem (10 servers) [NEW in V3]
├── E17: Compound Reliability Safeguard [NEW in V3]
└── E18: Real-Time Cost Transparency [NEW in V3]

KNOWLEDGE:
├── Verified Authority Registry (pgvector-enabled)
├── Jurisdiction Rules Engine
├── Case Knowledge Store (22 extraction sections)
├── Judge Profile Database (outcome-informed via E14)
├── Opposing Counsel Database (E15)
├── Court-Specific Template Registry
└── Case Law + Legislative + Regulatory Monitoring (E9)

AGENT PACKS:
├── Legal Litigation Pack (all-Opus, 5 agents, 18 enhancements)
├── Construction Management Pack (tiered models, 6 agents)
├── Business Operations Pack (tiered models, 5 agents)
└── Custom Pack Builder (API/SDK for developers)
```

---

## VERSION LOG

| Version | Date | Source | Key Changes |
|---------|------|--------|-------------|
| V1 (Runbook) | Mar 7 | DualAI prototype documentation | Infrastructure only, prototype architecture |
| V2 | Mar 15 | Deep research + Claude Code roadmap + enhancements | Full product spec, 12 enhancements, competitive analysis |
| **V3** | **Mar 15** | **Claude Code WDC analysis (5-agent panel, 7.725/10)** | **All-Opus for legal, E13-E18, Westlaw cost correction, verification chains, opposing counsel profiling, 10 MCP servers, drafting/Red Team depth** |

---

**CONFIDENTIAL — Bo Pennington / Pentek Design Build LLC**

*Ciphergy V3.0 — Five AI minds. Eighteen winning edge features. One mission: make the opposing party's rational choice crystal clear.*
