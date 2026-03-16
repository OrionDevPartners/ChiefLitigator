# WDC REVIEW: CIPHERGY PRODUCT SPEC V2.0

## Date: 2026-03-15
## Type: Full WDC Review (5-Agent Panel)
## Subject: V2 Product Spec — Gap Analysis & Refinement Recommendations

---

# EXECUTIVE SUMMARY

The V2 spec is a strong synthesis of all prior documents — it merges the market analysis, 5-agent architecture, 12 winning edge enhancements, MCP-first integration, and pricing into a coherent product vision. However, **9 material gaps and 3 internal conflicts** require resolution before this spec is build-ready. The most critical: the spec has no ethical/liability framework for a legal AI product, an unresolved model tiering conflict, and missing compound reliability architecture.

---

# SECTION A: INTERNAL CONFLICTS

## Conflict 1: Model Tiering vs. All-Opus Requirement

**Where it surfaces:**
- Section 2 (Cost Management): "Model tiering via LiteLLM — Simple tasks → Haiku ($1/M input). Standard → Sonnet ($3/M). Complex reasoning → Opus ($15/M)"
- Section 3 (Agent Architecture): "5 Agents" with no model specification per agent
- User requirement (original prompt): "using only opus 4.6 [1 mill] but use 5 total opus 4.6 [1mill]"

**The conflict:** The spec presents cost-optimized model tiering AND an all-Opus agent architecture without acknowledging they contradict each other.

**Resolution recommendation:**

For the **Legal Litigation Pack specifically**, all 5 agents run on Opus 4.6 (1M). The reasoning:
- A citation verification routed to Haiku could miss a statute amendment — catastrophic for a pro se litigant
- A deadline computation on Sonnet might not catch a local rule exception — catastrophic
- Legal work has no "simple tasks" — every interaction has consequences

For **other agent packs** (Construction, Business Ops) and for **non-substantive operations** within the legal pack (logging, formatting, file naming), model tiering is appropriate.

**Spec edit:** Add a `model_policy` field to the agent pack manifest:

```yaml
pack:
  name: "Legal Litigation Pack"
  model_policy: "all_reasoning"  # All agents use top-tier model
  model_override: "claude-opus-4-6"  # Explicit model lock

# vs.

pack:
  name: "Construction Management Pack"
  model_policy: "tiered"  # Route by task complexity
```

Cost mitigation for all-Opus legal: prompt caching (90% reduction on cached reads) + Batch API (50% reduction for background research) + independent scratchpads (67% token reduction). These three together make all-Opus viable at the $29 price point for moderate usage.

---

## Conflict 2: 7-Agent Compass vs. 5-Agent Architecture

**Where it surfaces:**
- Section 3 defines 5 agents (Lead, Research, Drafting, Red Team, Compliance)
- The Compass artifact described 7 agents for the legal pack (adding Filing Manager + Client Communicator)
- Section 7 (Agent Pack) says "Legal Litigation Pack — 5 agents"

**Status:** This was resolved correctly in V2 — Filing Manager duties folded into Compliance Counsel, Client Communicator folded into Lead Counsel. But the spec should explicitly state this decision and why, so future developers don't re-add agents that would fragment responsibility.

**Spec edit:** Add a footnote or ADR reference in Section 3:

> *The Legal Litigation Pack uses 5 agents rather than 7. Filing management (e-filing, service tracking) is owned by Compliance Counsel, which already owns all procedural requirements. Client communication is owned by Lead Counsel, which already owns the user interface. Separating these into independent agents would fragment accountability for deadlines and strategy respectively.*

---

## Conflict 3: Phase Timeline vs. @L:012

**Where it surfaces:**
- Section 11 assigns week ranges to each phase (Phase 0: Weeks 1-2, Phase 1: Weeks 3-5, etc.)
- User preference @L:012: "No timeline roadmaps — approved work executes immediately"

**Resolution:** Remove week estimates from the spec. Replace with dependency ordering only:

```
Phase 0 → Phase 1 → Phase 2 (can parallel with Phase 1)
Phase 2 + Phase 3 → Phase 4
Phase 4 + Phase 5 → Phase 6
Phase 6 → Phase 7 → Phase 8
```

Execution order is what matters, not calendar dates.

---

# SECTION B: MATERIAL GAPS

## Gap 1: NO ETHICAL / LIABILITY FRAMEWORK (CRITICAL)

**Risk level: CRITICAL — this is a legal AI product**

The V2 spec has zero treatment of:

### Unauthorized Practice of Law (UPL) Risk
Every US state prohibits the unauthorized practice of law. An AI system that provides legal advice, drafts legal documents, and recommends litigation strategy operates in this zone. The spec must include:

1. **System-level disclaimers (non-removable):**
   - "Ciphergy is an AI tool, not a lawyer. It does not provide legal advice and does not create an attorney-client relationship."
   - "All output must be reviewed by the user before filing with any court."
   - "AI-generated legal citations may be incorrect. Verify all citations independently."
   - "Communications with AI systems are generally NOT protected by attorney-client privilege."
   - "This system cannot appear in court, sign documents, or file on your behalf."

2. **Session-start warnings:**
   - Privilege warning (from Amendment 1.0, Section XIX.B)
   - Deadline verification warning ("independently verify all deadlines")
   - State-specific UPL disclosure as required by jurisdiction

3. **Per-output disclaimers:**
   - Every substantive legal analysis includes a confidence flag (High/Moderate/Low)
   - Every citation includes verification status
   - Every filing draft includes "DRAFT — WORK PRODUCT — NOT FOR FILING" until user designates final

4. **Terms of Service requirements:**
   - User acknowledges they are responsible for all filings and court appearances
   - User acknowledges AI output may contain errors
   - User acknowledges no attorney-client privilege
   - Limitation of liability clause
   - Mandatory arbitration? (consider carefully — ironic for a litigation tool)

### Regulatory Compliance
- **EU AI Act Article 14** — Already mentioned in Compass for HITL gates. But the legal domain is HIGH-RISK under the EU AI Act. This means:
  - Mandatory risk assessment documentation
  - Human oversight requirements (which WDC + user approval gates satisfy)
  - Transparency obligations (which the audit trail satisfies)
  - Data quality requirements (which the anti-hallucination loop partially satisfies)
- **State bar association rules** — Several states are developing AI-in-legal-practice guidelines. The spec should track these.
- **ABA Model Rules** — Rule 1.1 (competence) requires lawyers to understand technology they use. Ciphergy should help attorney users satisfy this by providing clear documentation of how the system works.

**Spec addition:** New Section 14: ETHICAL & LEGAL FRAMEWORK

---

## Gap 2: NO DATA PRIVACY / SECURITY ARCHITECTURE (CRITICAL)

**Risk level: CRITICAL — this handles case data, evidence, and potentially privileged communications**

The V2 spec mentions RLS, JWT, and RBAC (access control) but doesn't address:

### Data in Transit
- TLS 1.3 on all connections (standard but must be stated)
- Certificate pinning for mobile clients

### Data at Rest
- Postgres encryption at rest (AWS Aurora provides this)
- Application-level encryption for sensitive fields (case facts, evidence, strategy)
- Key management via AWS KMS or Secrets Manager

### Data at the LLM Provider
This is the critical question for a legal tool:

| Provider | Training on Data? | Data Retention | BAA Available? |
|----------|------------------|----------------|----------------|
| Anthropic API | No (API data not used for training) | 30-day log retention (can opt out) | Yes |
| OpenAI API | No (API data not used for training by default) | 30-day retention | Yes |
| Google Vertex | No (customer data not used) | Configurable | Yes |

**The spec must state:**
1. All LLM API calls use providers' zero-retention or minimum-retention options
2. No case data is used for model training by any provider
3. Users are informed which provider processes their data
4. For Enterprise tier: option for on-premises / VPC deployment where data never leaves the tenant's cloud

### Compliance Standards
- **SOC 2 Type II** — Already mentioned for Enterprise tier. Should be a Phase 8 deliverable.
- **HIPAA** — If medical records enter the system (family law cases often involve medical, personal injury always does). Requires BAA with all providers.
- **GDPR** — If European users access the platform
- **CCPA** — California users
- **State data breach notification** — Every state has different requirements. The system must have an incident response plan.

### Data Isolation
- Tenant data isolation via RLS (already in spec) — good
- Separate encryption keys per tenant? (Enterprise tier consideration)
- Data deletion on account closure (right to be forgotten)
- Export capability (user owns their data — provide full case extraction on demand)

**Spec addition:** New Section 15: DATA PRIVACY & SECURITY ARCHITECTURE

---

## Gap 3: COMPOUND RELIABILITY ARCHITECTURE MISSING

**Risk level: HIGH — directly affects system accuracy**

The Compass cited: at 85% per-action accuracy, a 10-step workflow succeeds only 20% of the time. The V2 spec mentions this stat (Section 12, bullet 2 on observability) but doesn't implement the solution.

The WDC Compass Analysis (E17) defined verification chains:

```
TRADITIONAL (compound failure risk):
Research → Draft → Review → File
0.85 × 0.85 × 0.85 × 0.85 = 52% success

CIPHERGY APPROACH (verification at each step):
Research → VERIFY research → Draft using VERIFIED research →
VERIFY draft → Review → VERIFY review → Deliver
Effective: 0.9775^4 = 91.2% success
```

**Implementation in agent architecture:**
1. Research Counsel generates citations → Citation Verification Pipeline confirms each one → only confirmed citations advance to Drafting
2. Drafting Counsel produces draft → Red Team + Compliance review in parallel → only passing drafts advance to Lead Counsel
3. Lead Counsel packages output → final confidence check → only certified output reaches user

Each agent's output is **independently verified** before becoming input to the next agent. This is the architectural pattern that makes multi-agent legal work reliable.

**Spec edit:** Add to Section 3 (Agent Architecture) as a subsection: "Verification Chain Architecture"

---

## Gap 4: E13-E18 NOT INCORPORATED

The WDC Compass Analysis identified 6 additional enhancements. The V2 spec includes E1-E12 but not:

| Enhancement | What It Adds | Where in V2 |
|-------------|-------------|-------------|
| **E13: What-If Strategy Branching** | Fork case state at decision points, model multiple litigation paths | Should be in Section 3 (leverages checkpointing already described) |
| **E14: Outcome-Based Learning** | Track case outcomes to improve future recommendations | Should be in Section 9 (Observability) |
| **E15: Opposing Counsel Profiling** | Analyze opposing attorney's litigation history, patterns, tendencies | Listed as V3 candidate (#6) — should be promoted to V2 |
| **E16: MCP Legal Tool Ecosystem** | 10 custom legal MCP servers, open-sourced for ecosystem | Partially covered in Section 5 — needs explicit build list |
| **E17: Compound Reliability Safeguard** | Verification chains for compound accuracy | See Gap 3 above |
| **E18: Real-Time Cost Transparency** | Per-deliverable cost tracking with attorney-fee comparison | Should be in Section 9 (Observability dashboard) |

**Recommendation:**
- E13, E15, E17: Promote to V2 core (high strategic value)
- E14, E18: Add to Section 9 (Observability)
- E16: Expand Section 5 MCP build list with explicit open-source strategy

---

## Gap 5: NO DOCUMENT VERSIONING / REVISION TRACKING

**Risk level: MEDIUM-HIGH**

When WDC sends a draft back for revision (scored 5.0-6.9 = "REVISION REQUIRED"), the user needs to:
1. See what changed between versions
2. Understand why it changed (which agent flagged what)
3. Compare the original draft to the revised draft
4. Approve or request further revision

The spec mentions checkpointing (Section 3) but doesn't connect it to document revision:

**Spec addition to Section 4 (within Drafting Counsel's capabilities):**

```
DOCUMENT REVISION TRACKING

Version 1 (Initial Draft)
├── Red Team Score: 6.2 — "Argument in Section III.B lacks supporting
│   authority for consequential damages foreseeability"
├── Compliance Score: 9.0 — "All procedures correct"
├── Research Score: 5.5 — "Citation to Smith v. Jones is unverified;
│   holding may not support the proposition stated"
├── COMPOSITE: 6.4 — REVISION REQUIRED
│
│ REVISIONS APPLIED:
│ ├── [Research] Replaced Smith v. Jones with Johnson v. Williams
│ │   (2024), verified via CourtListener — directly supports
│ │   foreseeability argument
│ ├── [Drafting] Rewrote Section III.B to lead with Johnson holding
│ └── [Red Team] Re-scored: 8.1 — "Argument now supported"
│
Version 2 (Revised Draft)
├── Red Team Score: 8.1
├── Compliance Score: 9.0
├── Research Score: 8.5
├── COMPOSITE: 8.4 — CERTIFIED WITH NOTES
└── NOTE: "Consider adding Restatement (Second) of Contracts §351
    for additional authority" [Research Counsel, advisory only]
```

---

## Gap 6: NO BATCH DOCUMENT INTAKE ARCHITECTURE

**Risk level: MEDIUM**

A real case intake involves uploading 20-100 documents: the complaint, prior correspondence, contracts, photos, invoices, court orders, discovery, etc. The spec describes document processing (from Amendment 1.0) but doesn't address **batch intake**.

**What's needed:**

```
BATCH INTAKE PIPELINE

User uploads 47 documents
         │
         ▼
    PARALLEL TRIAGE (all 47 simultaneously)
    ├── Classify each document type
    ├── Extract metadata (dates, parties, case numbers)
    ├── Flag priority documents (court orders with deadlines)
    └── Queue for deep analysis
         │
         ▼
    PRIORITY PROCESSING
    ├── Court orders → Compliance (extract deadlines FIRST)
    ├── Complaint → Research (identify claims, elements, defenses)
    ├── Contracts → Research (clause analysis)
    └── Everything else → queued by relevance
         │
         ▼
    CASE KNOWLEDGE STORE POPULATION
    ├── Timeline auto-populated from extracted dates
    ├── Party list auto-populated from extracted names
    ├── Evidence inventory auto-populated
    └── Claim matrix seeded from complaint analysis
         │
         ▼
    LEAD COUNSEL SUMMARY
    ├── "47 documents processed. Here's what I found..."
    ├── Immediate deadline alerts (if any)
    ├── Case assessment with confidence level
    └── Recommended next steps
```

**Spec addition:** Section 3 subsection: "Batch Document Intake Pipeline"

---

## Gap 7: NO OFFLINE / COURTROOM MODE

**Risk level: MEDIUM**

Pro se litigants use this system in courtrooms where:
- WiFi may be unreliable or unavailable
- They need instant access to case data, timelines, and key arguments
- They can't wait for API calls to complete

**What's needed:**

A **cached local mode** that includes:
1. Case summary and theory (pre-generated)
2. Key timelines and dates
3. Evidence inventory with key documents
4. Argument outlines for the hearing topic
5. Objection quick-reference card
6. Judge profile card
7. Deadline inventory

This is a **pre-hearing preparation export** — generated before court, available offline as a PDF or cached in the mobile app (if Expo React Native is built).

**Spec addition:** Section 8 (Pro Se Features) item #8: "Courtroom Ready Pack — offline-accessible case briefing for hearing preparation"

---

## Gap 8: NO TESTING STRATEGY FOR LEGAL ACCURACY

**Risk level: HIGH**

The spec mentions "Load testing and cost optimization" in Phase 8 but nothing about testing **legal accuracy** — which is the entire value proposition.

**What's needed:**

### Unit Tests
- Deadline computation: Given [jurisdiction, event, method of service], assert [correct deadline]
- Citation format: Given [case], assert [correct Bluebook format]
- Element extraction: Given [claim type, jurisdiction], assert [correct elements list]

### Integration Tests
- CourtListener MCP: Given [search query], verify [real results returned]
- Citation verification: Given [known real citation], verify [passes 5-step check]
- Citation verification: Given [known fabricated citation], verify [flagged as unverified]

### End-to-End Tests (Anonymized Real Cases)
- **The gold standard:** Take 10 anonymized real cases with known outcomes. Feed the facts into the system. Does it:
  - Identify the correct claims?
  - Find the correct statutes?
  - Cite real, verified case law?
  - Compute correct deadlines?
  - Identify the right defenses?
  - Produce a viable litigation strategy?
  - Draft a competent complaint?

### Adversarial Tests
- Feed the system fabricated citations and verify they're caught
- Feed contradictory facts and verify the system flags the inconsistency
- Feed expired statutes of limitations and verify the system warns

### Jurisdictional Coverage Tests
- For each supported jurisdiction: verify deadline rules, filing requirements, and statute formats

**Spec addition:** New Section 16: TESTING STRATEGY

---

## Gap 9: PENNINGTON STANDARD UNDEFINED

**Risk level: LOW — but creates confusion**

Referenced in:
- E10 (Pro Se Credibility Optimizer): "Professional formatting engine (Pennington Standard as template)"
- Phase 4: "Pennington Standard as default legal template"

But never defined. Is this:
- A formatting template derived from Pennington v. Campenni filings?
- A quality standard for legal document output?
- A specific court format?

**Resolution:** Either define it in the spec or replace with a generic reference to "court-standard professional formatting."

---

# SECTION C: ADDITIONAL REFINEMENTS

## Refinement 1: Revenue Model Projection

The spec has market sizing and pricing but no projection. At minimum:

```
SCENARIO: Conservative Year 1

Month 1-3:   Beta — 500 free users, 50 Pro ($29)
Month 4-6:   Launch — 2,000 free, 200 Pro, 10 Team ($49×3)
Month 7-9:   Growth — 5,000 free, 500 Pro, 30 Team
Month 10-12: Scale — 10,000 free, 1,000 Pro, 50 Team, 1 Enterprise

Year 1 ARR (Month 12 annualized):
  Pro:        1,000 × $29 × 12  = $348,000
  Team:       50 × 3 × $49 × 12 = $88,200
  Enterprise: 1 × $50,000        = $50,000
  TOTAL:                          = $486,200

Cost estimate (Year 1):
  Anthropic API: ~$15K/month at scale (prompt caching + batch)
  AWS infra:     ~$3K/month
  Cloudflare:    ~$500/month
  Total hosting: ~$222K/year
  Gross margin:  ~54%
```

## Refinement 2: Competitive Defense Strategy

What happens when Harvey AI ($8B valuation) decides to go downmarket? Or when CrewAI adds a legal agent pack?

**Defensive moats (in order of strength):**
1. **Outcome data** — Every case that runs through Ciphergy teaches the system what works. Competitors start at zero. (Requires E14: Outcome-Based Learning)
2. **MCP server ecosystem** — Open-source legal MCP servers that the community maintains. Competitors must build or adopt these same servers.
3. **Case Knowledge Store portability** — Users can export everything (Extraction Prompt). This builds trust, reduces churn anxiety, and paradoxically increases retention (users who know they CAN leave tend to stay).
4. **Pro se market focus** — Harvey targets $1,000+/seat BigLaw. CrewAI targets developers. Ciphergy targets the 72% of civil litigants who represent themselves. Different market, different product, different price point.
5. **Vertical depth** — The 18 enhancements (E1-E18) represent 6+ months of domain engineering. A horizontal platform can't replicate this depth without the same investment.

## Refinement 3: Onboarding UX Design

The spec says "5-minute time-to-value" but doesn't describe the flow:

```
ONBOARDING FLOW (Pro Se Legal)

Step 1: SIGN UP (30 seconds)
├── Email + password (or Google SSO)
└── 14-day Pro reverse trial starts automatically

Step 2: WHAT DO YOU NEED? (30 seconds)
├── "I received a lawsuit and need to respond"
├── "I want to file a lawsuit"
├── "I need help with a legal document"
├── "I have an ongoing case and need help"
└── [Each choice activates a specific workflow]

Step 3: TELL US ABOUT YOUR SITUATION (2 minutes)
├── Guided interview: jurisdiction, parties, what happened, what you want
├── Document upload (drag and drop)
└── System processes and classifies while user types

Step 4: YOUR CASE DASHBOARD (immediate)
├── Case summary (auto-generated from interview + documents)
├── Identified claims with confidence levels
├── Immediate deadlines (with urgency flags)
├── Recommended next steps
└── "Would you like to start with [most urgent action]?"

Step 5: FIRST DELIVERABLE (within 5 minutes of starting)
├── If responding to lawsuit: deadline alert + defense analysis
├── If filing: claim viability assessment + jurisdiction card
├── If document help: document analysis with actionable next steps
└── User sees immediate value — conversion moment
```

## Refinement 4: API Surface for Developer Extensibility

Section 10 mentions API access at Pro tier but doesn't describe it:

```
CIPHERGY API SURFACE

/api/v1/projects          — CRUD for cases/matters
/api/v1/projects/:id/agents — Agent configuration per project
/api/v1/projects/:id/runs   — Execute agent workflows
/api/v1/projects/:id/knowledge — Knowledge base CRUD
/api/v1/projects/:id/documents — Document upload/generation
/api/v1/projects/:id/timeline — Case timeline
/api/v1/projects/:id/claims  — Claim matrix
/api/v1/projects/:id/deadlines — Deadline inventory
/api/v1/projects/:id/extraction — Full 22-section extraction

/api/v1/agents              — Agent marketplace CRUD
/api/v1/packs               — Agent pack marketplace
/api/v1/mcp/servers         — MCP server registry
/api/v1/templates           — Document template CRUD

Webhooks:
  - agent.run.completed
  - deadline.approaching (14/7/3/1 day)
  - wdc.review.completed
  - compliance.veto.triggered
  - case.status.changed
```

This enables:
- Law firm practice management software integration
- Court filing automation providers building on Ciphergy
- Legal aid organizations building custom workflows
- Developer community extending agent capabilities

---

# SECTION D: WDC SCORING

## Agent Scores for V2 Spec Quality

| Agent | Score | Key Concern |
|-------|-------|-------------|
| Lead Counsel (30%) | 8.0 | Strong strategic vision; missing ethical framework is the gap |
| Research Counsel (25%) | 7.5 | Knowledge base well-designed; compound reliability missing |
| Drafting Counsel (15%) | 7.5 | Doc generation stack good; versioning/revision tracking absent |
| Red Team (20%) | 7.0 | E1-E12 integrated; E13 (what-if branching) not incorporated |
| Compliance (10% + VETO) | 6.5 | **CONDITIONAL VETO** — No ethical/UPL framework for a legal AI product is a compliance risk. No data privacy section. These must be added before build begins. |

## Composite Score

| Agent | Domain Score | Weight | Weighted |
|-------|-------------|--------|----------|
| Lead Counsel | 8.0 | 30% | 2.40 |
| Research Counsel | 7.5 | 25% | 1.875 |
| Drafting Counsel | 7.5 | 15% | 1.125 |
| Red Team | 7.0 | 20% | 1.40 |
| Compliance | 6.5 | 10% | 0.65 |
| **COMPOSITE** | | **100%** | **7.45** |

## Verdict: CERTIFIED WITH NOTES + CONDITIONAL COMPLIANCE FLAG

**Score: 7.45 — within CERTIFIED WITH NOTES range (7.0-8.4)**

**Compliance Conditional:** Not a full VETO (the spec doesn't violate rules), but Compliance flags that the **absence of an ethical/liability framework and data privacy architecture** must be resolved before any code is written. A legal AI product without UPL disclaimers, privacy controls, and liability limitations is a lawsuit waiting to happen — which would be deeply ironic.

---

# SECTION E: RECOMMENDED V2.1 ADDITIONS

To bring the spec from 7.45 to 8.5+ (CERTIFIED), add:

| Priority | Addition | Section |
|----------|----------|---------|
| **CRITICAL** | Ethical & Liability Framework (UPL, disclaimers, regulatory) | New Section 14 |
| **CRITICAL** | Data Privacy & Security Architecture | New Section 15 |
| **HIGH** | Compound Reliability / Verification Chains | Section 3 addition |
| **HIGH** | E13 (What-If Branching) + E15 (Opposing Counsel Profiling) | Section 4 |
| **HIGH** | Testing Strategy for Legal Accuracy | New Section 16 |
| **HIGH** | Model Policy per Pack (resolve tiering conflict) | Section 2 + Section 7 |
| **MEDIUM** | Document Versioning / Revision Tracking | Section 3/4 |
| **MEDIUM** | Batch Document Intake Pipeline | Section 3 |
| **MEDIUM** | E14 (Outcome Learning) + E18 (Cost Transparency) | Section 9 |
| **MEDIUM** | Courtroom Ready Pack (offline mode) | Section 8 |
| **MEDIUM** | Onboarding UX Flow | Section 10 or new section |
| **LOW** | Revenue Projection Model | Section 1 |
| **LOW** | Competitive Defense Strategy | Section 12 |
| **LOW** | API Surface Definition | Section 5 or new section |
| **LOW** | Pennington Standard definition | Section 4 |
| **LOW** | Remove week estimates (per @L:012) | Section 11 |

---

*WDC Review Complete. V2 Spec is a strong foundation. The gaps are addressable. The conflicts are resolvable. The product vision is sound.*

*Add the ethical framework and data privacy architecture first — everything else is a feature. Those two are a legal requirement for a legal product.*
