# CIPHERGY FINAL BUILD — COMPARISON, ANALYSIS & ROADMAP

## Owner: Bo Pennington | bo@symio.ai
## Date: 2026-03-15
## Status: PROPOSAL — Awaiting Approval

---

# PART 1: COMPARE & CONTRAST — THE THREE COMPONENTS

## Component Summary

| Component | Purpose | Maturity | Scope |
|-----------|---------|----------|-------|
| **CIPHERGY-REPO** | Dual-environment AI orchestration platform | Framework built, protocols defined, CLI/dashboard functional | Infrastructure + orchestration |
| **Legal_CoCounsel_Amendment_1.0** | Tool integration directives + legal workflow specifications | Specification complete, not yet wired into REPO | Legal domain operations |
| **Total_Case_Extraction_Prompt** | Zero-loss data portability between AI sessions | Standalone prompt, not integrated | Data preservation + migration |

---

## Detailed Comparison

### 1. Architecture

**CIPHERGY-REPO** implements a **two-agent model** (LOCAL + CLOUD) communicating through an **Asana message bus**. This is a human-bridged architecture — the operator moves data between environments manually with sync tools. The system includes:
- Cascade engine (trigger-based automation)
- File registry with MD5 hash integrity
- WDC Panel (3 personas: Strategist 40%, Red Team 35%, Evaluator 25%)
- 5 mesh agents (Onboarding, Evidence Coach, Deadline Sentinel, Draft Guardian, Strategy Advisor)
- Domain profiles (legal, medical, investigation, engineering)

**Amendment 1.0** specifies **what the system should do** in legal practice — tool integration directives (web search, Drive, Calendar, Asana, Gmail, Slack), document processing workflows, deadline computation rules, expanded practice areas, opposing counsel simulation, and file output standards. It's the operational playbook but has **no implementation code** — it's a system prompt supplement.

**Extraction Prompt** is a **standalone 22-section protocol** designed to be pasted into any AI session to export all case data. It's not integrated into either component — it operates as a manual portability tool.

### 2. Gaps Between Components

| Gap | Description | Impact |
|-----|-------------|--------|
| **Amendment not wired to REPO** | The 20+ operational directives in Amendment 1.0 have no corresponding code, cascade triggers, or agent behaviors in the REPO | The legal co-counsel capabilities exist only as a prompt, not as enforced system behavior |
| **Extraction not automated** | The 22-section extraction is a manual paste-and-run prompt — not an automated pipeline | Case data portability requires human intervention every time |
| **Two-agent model is limiting** | LOCAL + CLOUD architecture splits capabilities artificially (filesystem vs. web search) | A unified 5-agent Opus 4.6 (1M) model eliminates this split entirely |
| **WDC Panel is shallow** | Current WDC has 3 personas with basic scoring | Doesn't match the depth needed for legal output where a missed statute = malpractice |
| **No law database** | System relies on web search + AI training data for legal authority | No persistent, verified, jurisdiction-specific law corpus |
| **No document generation pipeline** | Amendment specifies .docx/.pdf output but REPO has no document rendering engine | Can't produce court-ready filings |
| **No case state machine** | No formal model tracking litigation phase, active deadlines, evidence status | System can't proactively manage case lifecycle |
| **Domain profiles are templates, not engines** | `legal.yaml` defines vocabulary and weights but doesn't drive behavior | Profile is cosmetic, not functional |
| **No hallucination verification loop** | WDC scores confidence but doesn't verify citations against actual sources | Citations could be fabricated without detection |
| **No jurisdictional rules engine** | Amendment mentions FRCP Rule 6, local rules, etc. but no structured rules data | Deadline computation is narrative, not programmatic |

### 3. What Each Component Does Well

**CIPHERGY-REPO excels at:**
- Infrastructure scaffolding (registry, cascade, CLI, dashboard)
- Communication protocol design (structured Asana messaging)
- Behavioral guardrails (6 protocol documents, non-negotiable constraints)
- Domain-agnostic design (profiles, templates, vocabulary mapping)

**Amendment 1.0 excels at:**
- Legal domain expertise (comprehensive practice area coverage)
- Tool integration specification (exactly how/when to use each connector)
- Document processing workflows (type-specific analyzers)
- Deadline management rigor (FRCP Rule 6, conservative computation, watchdog patterns)
- Opposing counsel simulation design (defense memos, cross-exam prep, stress testing)
- Risk quantification framework (6-factor viability matrix)

**Extraction Prompt excels at:**
- Completeness — 22 sections covering every dimension of a legal matter
- Structured output — immediately importable into a new system
- Zero-loss philosophy — "do not summarize, do not abbreviate"
- Self-verification — Section 21 checklist + Section 22 transfer readiness assessment

---

# PART 2: THE FIVE-AGENT ARCHITECTURE

## Design Philosophy

The current CIPHERGY-REPO splits work across two environments (CLI vs. Desktop) because of platform limitations. With **five Opus 4.6 (1M context) instances**, we eliminate that constraint entirely. Each agent gets:
- Full 1M context window (entire case files, full statutory texts, complete deposition transcripts)
- Independent reasoning chain (no cross-contamination of analysis)
- Defined role boundaries (specialization prevents scope creep)
- Structured inter-agent communication (debate protocol, not free-form chat)

The key innovation: **no agent's output reaches the user without passing through weighted debate consensus among all five agents.**

---

## The Five Agents

### AGENT 1: LEAD COUNSEL (The Strategist)
**Role:** Case commander. Owns the litigation strategy, coordinates all agents, interfaces with the user.

| Attribute | Detail |
|-----------|--------|
| **Primary Duties** | Case intake, matter classification, strategy formulation, phase management, user communication, final output approval |
| **Debate Weight** | 30% — Highest individual weight because strategy alignment determines case direction |
| **Context Priority** | Full case narrative, procedural posture, strategic history, user goals and risk tolerance |
| **Skills** | Litigation strategy (all phases), settlement analysis, case theory development, narrative construction, risk-adjusted decision making, jury/bench trial calculus |
| **Unique Responsibility** | Writes the "theory of the case" that all other agents must align with. Only agent that can modify overall strategy. |
| **Triggers From User** | New matter intake, strategy questions, settlement discussions, "what should I do next?", any ambiguous request |

**What Lead Counsel Owns:**
- Executive case summary (Section 1 of extraction)
- Overall strategy and tactical analysis (Section 12)
- Settlement strategy and posture
- Phase transition decisions (when to move from discovery to motions, etc.)
- Final sign-off on all deliverables before user sees them

---

### AGENT 2: RESEARCH & CITATION COUNSEL (The Scholar)
**Role:** Legal research engine. Finds, verifies, and validates every legal authority the system relies on.

| Attribute | Detail |
|-----------|--------|
| **Primary Duties** | Statute lookup, case law research, citation verification, jurisdiction-specific rule identification, legislative amendment tracking, authority synthesis |
| **Debate Weight** | 25% — Critical for accuracy; a fabricated citation is catastrophic |
| **Context Priority** | Jurisdiction config, claims at issue, legal theories, statutory texts, case law corpus, court rules |
| **Skills** | Legal research methodology, citation format (Bluebook/ALWD), statutory interpretation, case law analysis, Shepardizing/KeyCiting logic, regulatory research |
| **Unique Responsibility** | EVERY citation in ANY output must be verified by this agent. Maintains the "Verified Authority Registry" — a running list of confirmed-good citations with verification timestamps. |
| **Triggers From User** | "Find case law on...", "What's the statute for...", "Is this citation real?", any legal question |

**What Research Counsel Owns:**
- Legal research & authorities (Section 10 of extraction)
- Citation audit standard (Amendment XIV.C — 5-step verification)
- Verified Authority Registry (new — persistent citation database)
- Jurisdiction quick-reference cards (Amendment XVI.B)
- Statute of limitations / prescription tracking
- Legislative amendment monitoring

**Anti-Hallucination Protocol:**
1. Never cite from memory alone — every citation must be web-searched
2. If verification fails after 3 search attempts → flag as `[UNVERIFIED]`
3. Cross-reference holdings: does the case actually say what we claim?
4. Check current status: has the statute been amended? Is the case still good law?
5. Maintain verification log: citation → search queries used → sources found → verification status

---

### AGENT 3: DRAFTING COUNSEL (The Scrivener)
**Role:** Produces every written deliverable — motions, pleadings, briefs, memoranda, correspondence, discovery.

| Attribute | Detail |
|-----------|--------|
| **Primary Duties** | Document drafting, formatting to court specifications, argument construction, factual narrative writing, exhibit preparation, response/reply drafting |
| **Debate Weight** | 15% — Output quality matters but strategy and research outweigh drafting in debate |
| **Context Priority** | Strategy from Lead Counsel, authorities from Research Counsel, court formatting rules, prior filings, judge's preferences |
| **Skills** | Legal writing (persuasive + objective), court formatting (federal + state), citation integration, document structure, plain language drafting for pro se users, .docx/.pdf generation |
| **Unique Responsibility** | All written output is drafted by this agent. Never generates legal authority — receives verified citations from Research Counsel only. |
| **Triggers From User** | "Draft a motion to...", "Write a response to...", "Prepare a demand letter", any document request |

**What Drafting Counsel Owns:**
- Documents drafted & work product (Section 11 of extraction)
- File output standards (Amendment X.G)
- Court-specific formatting
- Document processing workflows (Amendment XI.B — type-specific analyzers)
- Template generation (Amendment XVI.A)
- Matter file organization (Amendment XVIII)

**Drafting Rules:**
1. Never invent citations — only use authorities provided by Research Counsel
2. Every draft includes "DRAFT — WORK PRODUCT" header until user designates final
3. Arguments must map to strategy set by Lead Counsel
4. Factual assertions must be traceable to evidence in the record
5. Jurisdictional procedure (filing requirements, page limits, font rules, caption format) verified before any draft

---

### AGENT 4: ADVERSARIAL COUNSEL (The Red Team)
**Role:** Attacks every output from the opposing party's perspective. Stress tests every strategy, filing, and argument.

| Attribute | Detail |
|-----------|--------|
| **Primary Duties** | Opposing counsel simulation, defense memo generation, cross-examination prep, argument stress testing, weakness identification, risk quantification |
| **Debate Weight** | 20% — Adversarial review prevents blind spots that lose cases |
| **Context Priority** | All case facts, opposing party's known positions, evidence inventory, claims/defenses analysis, prior court rulings in similar cases |
| **Skills** | Defense strategy, motion to dismiss analysis, summary judgment vulnerability assessment, cross-examination technique, impeachment identification, settlement leverage analysis, jury psychology |
| **Unique Responsibility** | Must produce a counter-argument for EVERY substantive output before it reaches the user. If Red Team cannot find a flaw, the output is stronger for it. If Red Team finds a flaw, it must be addressed before delivery. |
| **Triggers** | Automatic — fires on every substantive output. Also on-demand for "stress test this", "what will opposing counsel argue?", "prepare me for cross" |

**What Adversarial Counsel Owns:**
- Defenses, counterclaims & opposition analysis (Section 5 of extraction)
- Stress testing & risk analysis (Section 6 of extraction)
- Enhanced opposing counsel simulation (Amendment XVII)
- Quantified risk assessment framework (Amendment XV)
- Cross-examination preparation
- Pre-filing vulnerability scan

**Red Team Protocol:**
1. For every motion/brief: write a 1-page opposition memo identifying the 3 strongest counter-arguments
2. For every strategy recommendation: identify the 3 most likely ways it fails
3. For every citation: challenge its applicability — does it actually support what we claim?
4. For every factual assertion: identify what evidence the opposing party would use to contradict it
5. Score output on 6-factor viability matrix (Amendment XV.A) before allowing delivery

---

### AGENT 5: COMPLIANCE & PROCEDURE COUNSEL (The Sentinel)
**Role:** Jurisdictional rules, deadlines, procedural requirements, error checking, and case lifecycle management.

| Attribute | Detail |
|-----------|--------|
| **Primary Duties** | Deadline computation, jurisdictional rule verification, filing requirement compliance, procedural error detection, case phase tracking, statute of limitations monitoring, court rule application |
| **Debate Weight** | 10% — Procedural compliance is binary (right or wrong), not nuanced, so weight is lower but veto power is absolute on procedural errors |
| **Context Priority** | Jurisdiction config, court rules (local/state/federal), case schedule, deadline inventory, filing requirements, service rules |
| **Skills** | FRCP/state rule mastery, deadline computation (Rule 6 + state equivalents), e-filing requirements, service of process rules, local rule compliance, judicial standing orders |
| **Unique Responsibility** | **VETO POWER** — Can block ANY output that violates a procedural rule, misses a deadline, or misstates a jurisdictional requirement, regardless of debate scores. Procedural errors are not debatable. |
| **Triggers** | Automatic — fires on every output. Also maintains proactive deadline warnings (90-day, 30-day, 14-day, 7-day, 3-day alerts) |

**What Compliance Counsel Owns:**
- Active deadline tracking (Amendment XII)
- Deadline computation rules (Amendment XII.B)
- Prescription/statute of limitations watchdog (Amendment XII.C)
- Jurisdictional & procedural framework (Section 15 of extraction)
- Filing requirement verification
- Service of process compliance
- Case state machine (new — tracks current litigation phase, what's due, what's overdue)

**Compliance Rules:**
1. VETO authority on procedural violations — no debate override
2. Every deadline computed using conservative interpretation (earlier date when ambiguous)
3. Court holiday schedules verified via web search, not memory
4. Filing requirements checked against current court website before any filing
5. Maintains running deadline inventory visible to all agents and user

---

## Inter-Agent Communication Protocol

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                           │
│        (uploads context, facts, evidence, questions)         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              AGENT 1: LEAD COUNSEL (30%)                     │
│   Receives input → classifies → assigns to agents →         │
│   coordinates debate → delivers final output to user         │
└───┬──────────┬──────────┬──────────┬────────────────────────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│AGENT 2 │ │AGENT 3 │ │AGENT 4 │ │AGENT 5 │
│Research│ │Drafting│ │Red Team│ │Compli- │
│Scholar │ │Scriven.│ │Advers. │ │ance    │
│ (25%)  │ │ (15%)  │ │ (20%)  │ │ (10%)  │
│        │ │        │ │        │ │ VETO   │
└────────┘ └────────┘ └────────┘ └────────┘
```

---

## Weighted Debate Consensus Protocol (WDC v2.0)

### Trigger
Every substantive output (motions, strategies, legal analysis, case assessments, recommendations) must pass WDC before reaching the user.

### Process

**Phase 1: Generation (Parallel)**
- Lead Counsel formulates the strategic approach
- Research Counsel gathers and verifies all authorities
- Drafting Counsel produces the written output
- All three work in parallel where possible

**Phase 2: Adversarial Review**
- Red Team Agent receives the draft and produces counter-analysis
- Compliance Agent checks all procedural/jurisdictional elements
- Both reviews happen in parallel

**Phase 3: Debate & Scoring**
Each agent scores the output on their domain:

| Agent | Score Domain | Weight | Veto Power |
|-------|-------------|--------|------------|
| Lead Counsel | Strategic alignment, case theory consistency, user goals | 30% | No |
| Research Counsel | Citation accuracy, authority relevance, legal basis strength | 25% | No |
| Drafting Counsel | Writing quality, argument clarity, formatting compliance | 15% | No |
| Red Team | Vulnerability exposure, counter-argument resilience | 20% | No |
| Compliance | Procedural correctness, deadline accuracy, jurisdictional compliance | 10% | **YES** |

**Scoring Scale:** 0-10 per agent, weighted to composite score.

**Phase 4: Certification**

| Composite Score | Certification | Action |
|-----------------|--------------|--------|
| 8.5 - 10.0 | **CERTIFIED** | Deliver to user |
| 7.0 - 8.4 | **CERTIFIED WITH NOTES** | Deliver with flagged concerns |
| 5.0 - 6.9 | **REVISION REQUIRED** | Return to Phase 1 with specific feedback |
| Below 5.0 | **REJECTED** | Fundamental rethink required — escalate to user |
| Any Compliance VETO | **BLOCKED** | Fix procedural issue before any other action |

**Phase 5: Delivery**
- Lead Counsel packages the certified output
- Includes confidence assessment, flagged concerns, and recommended verification steps
- User receives the deliverable + a brief "Debate Summary" showing scores and any dissenting notes

### Light Review (Expedited)
For non-substantive outputs (status updates, clarifying questions, file organization):
- Lead Counsel + one other agent review
- Composite threshold: 7.0
- No full debate required

---

# PART 3: DATA SIPHONING & LAW CORPUS ARCHITECTURE

## The Problem
AI models hallucinate legal citations. Training data goes stale. Statutes get amended. Cases get overruled. A pro se litigant can't afford to file a motion based on a fabricated case.

## The Solution: Verified Legal Knowledge Base (VLKB)

### Layer 1: Ingestion Sources

| Source | Type | Access Method | Coverage |
|--------|------|---------------|----------|
| **CourtListener / RECAP** | Case law, opinions, dockets | Free API (courtlistener.com/api/) | Federal + many state courts |
| **US Code (uscode.house.gov)** | Federal statutes | Bulk XML download + API | Complete USC |
| **eCFR (ecfr.gov)** | Federal regulations | Free API | Complete CFR |
| **State legislature sites** | State statutes | Web scraping per state | Jurisdiction-specific |
| **Google Scholar (scholar.google.com)** | Case law search | Web search integration | Broad coverage |
| **Congress.gov** | Federal legislative history | Free API | Bills, amendments, legislative history |
| **PACER/CM-ECF** | Federal court filings, dockets | API ($0.10/page, capped at $3/doc) | All federal courts |
| **State court e-filing portals** | State court filings | Per-court API/scraping | Jurisdiction-specific |
| **Cornell LII (law.cornell.edu)** | Statutes, regulations, case summaries | Free, web scraping | Comprehensive reference |
| **Casetext/Fastcase (free tiers)** | Case law research | API where available | Varies |

### Layer 2: Verified Authority Registry (VAR)

Every citation the system uses gets entered into a persistent database:

```
{
  "citation_id": "uuid",
  "citation_text": "Smith v. Jones, 523 U.S. 100 (2004)",
  "type": "case_law",
  "jurisdiction": "federal_supreme",
  "verified": true,
  "verification_date": "2026-03-15",
  "verification_method": "courtlistener_api",
  "verification_sources": ["https://courtlistener.com/opinion/..."],
  "holding_summary": "...",
  "key_quotes": ["..."],
  "still_good_law": true,
  "last_checked": "2026-03-15",
  "used_in_matters": ["matter_001"],
  "tags": ["breach_of_contract", "damages", "mitigation"]
}
```

### Layer 3: Jurisdiction Rules Engine

Structured data for each jurisdiction the user operates in:

```yaml
jurisdiction:
  name: "Louisiana"
  type: "state"
  court_system:
    trial: "District Courts"
    appellate: "Courts of Appeal (5 circuits)"
    supreme: "Louisiana Supreme Court"
  rules:
    civil_procedure: "Louisiana Code of Civil Procedure"
    evidence: "Louisiana Code of Evidence"
    local_rules_url: "https://..."
  deadlines:
    answer_to_complaint:
      days: 15
      type: "calendar"
      source: "La. C.C.P. art. 1001"
      exceptions: ["service by domiciliary: 30 days"]
    discovery:
      interrogatories_response: 15
      rfp_response: 15
      rfa_response: 15
    appeal_notice: 60
    new_trial_motion: 7
  filing:
    e_filing_system: "..."
    e_filing_url: "..."
    filing_fees:
      civil_petition: "$..."
      motion: "$..."
    format_requirements:
      paper_size: "letter"
      margins: "1 inch"
      font: "Times New Roman 12pt or equivalent"
      line_spacing: "double"
  holidays: [...]  # Updated annually via web search
```

### Layer 4: Case Knowledge Store

Per-matter persistent storage that survives across sessions (maps to Extraction Prompt sections):

```
matter_001/
├── executive_summary.md          (Section 1)
├── parties.json                  (Section 2)
├── timeline.json                 (Section 3)
├── claims/                       (Section 4)
│   ├── claim_001_breach.json
│   └── claim_002_negligence.json
├── defenses/                     (Section 5)
├── risk_analysis/                (Section 6)
├── evidence/                     (Section 7)
│   ├── inventory.json
│   └── documents/
├── discovery/                    (Section 8)
├── motions/                      (Section 9)
├── authorities/                  (Section 10)
├── work_product/                 (Section 11)
├── strategy/                     (Section 12)
├── communications/               (Section 13)
├── financials/                   (Section 14)
├── jurisdiction/                 (Section 15)
├── insurance/                    (Section 16)
├── open_questions/               (Section 17)
├── action_items/                 (Section 18)
├── lessons/                      (Section 19)
├── debate_logs/                  (WDC audit trail)
└── extraction_snapshots/         (Full extraction backups)
```

---

# PART 4: ROADMAP — BUILD PHASES

## Phase 0: Foundation (Week 1-2)
**Goal:** Restructure CIPHERGY-REPO for 5-agent architecture

| Task | Description | Priority |
|------|-------------|----------|
| 0.1 | Architect the 5-agent orchestration layer — replace dual-agent LOCAL/CLOUD model with 5 Opus 4.6 (1M) agent model | CRITICAL |
| 0.2 | Define agent communication protocol — structured JSON messages between agents (replaces Asana bus for inter-agent comms) | CRITICAL |
| 0.3 | Design the WDC v2.0 debate engine — weighted scoring, veto logic, audit logging | CRITICAL |
| 0.4 | Design Case Knowledge Store schema — per-matter structured storage (maps to extraction sections) | CRITICAL |
| 0.5 | Define user interface contract — how user uploads context/evidence, how system returns deliverables | HIGH |
| 0.6 | Migrate existing guardrails, input gates, and behavioral protocols to new architecture | HIGH |

**Deliverable:** Architecture document (ADR), agent protocol specs, data schemas

---

## Phase 1: Agent Core (Week 3-5)
**Goal:** Build and wire the 5 agents with debate consensus

| Task | Description | Priority |
|------|-------------|----------|
| 1.1 | Build Agent 1 (Lead Counsel) — case intake, routing, strategy engine, user interface | CRITICAL |
| 1.2 | Build Agent 2 (Research Counsel) — legal research pipeline, citation verification, VAR integration | CRITICAL |
| 1.3 | Build Agent 3 (Drafting Counsel) — document generation, formatting, template engine | CRITICAL |
| 1.4 | Build Agent 4 (Red Team) — adversarial review, stress testing, risk scoring | CRITICAL |
| 1.5 | Build Agent 5 (Compliance) — deadline engine, jurisdictional rules, procedural checking, veto logic | CRITICAL |
| 1.6 | Build WDC v2.0 debate orchestrator — runs parallel review, collects scores, enforces thresholds | CRITICAL |
| 1.7 | Build inter-agent message bus — structured communication with audit trail | HIGH |
| 1.8 | Integrate agent system prompts — wire Amendment 1.0 directives into each agent's behavioral protocol | HIGH |

**Deliverable:** 5 functional agents that can receive input, process it, debate, and return certified output

---

## Phase 2: Legal Knowledge Engine (Week 4-6, parallel with Phase 1)
**Goal:** Build the Verified Legal Knowledge Base

| Task | Description | Priority |
|------|-------------|----------|
| 2.1 | Build CourtListener API connector — case law search, opinion retrieval, docket access | CRITICAL |
| 2.2 | Build US Code / eCFR connector — statute and regulation lookup | CRITICAL |
| 2.3 | Build Verified Authority Registry (VAR) — persistent citation database with verification status | CRITICAL |
| 2.4 | Build Jurisdiction Rules Engine — structured deadline rules, filing requirements, court info per jurisdiction | HIGH |
| 2.5 | Build Google Scholar legal search connector — backup case law verification | HIGH |
| 2.6 | Build state statute connectors — top 10 states first (LA, TX, CA, NY, FL, IL, GA, OH, PA, VA) | HIGH |
| 2.7 | Build citation verification pipeline — 5-step audit (exists → format → holding → good law → current) | CRITICAL |
| 2.8 | Build anti-hallucination loop — every citation must pass verification before appearing in any output | CRITICAL |

**Deliverable:** Working legal research engine with verified citations, jurisdiction rules, and anti-hallucination guarantees

---

## Phase 3: Case Management Engine (Week 5-7)
**Goal:** Build the case lifecycle system

| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Build Case Knowledge Store — per-matter structured storage (22 extraction sections) | CRITICAL |
| 3.2 | Build case state machine — tracks litigation phase, transitions, active deadlines | CRITICAL |
| 3.3 | Build deadline engine — computation (Rule 6 + state equivalents), proactive warnings, calendar integration | CRITICAL |
| 3.4 | Build evidence inventory system — document upload, classification, authentication tracking | HIGH |
| 3.5 | Build extraction automation — auto-generate full 22-section extraction on demand (replaces manual prompt) | HIGH |
| 3.6 | Build document processing pipeline — intake sequence from Amendment XI (complaint analyzer, motion analyzer, contract reviewer, discovery processor, etc.) | HIGH |
| 3.7 | Build claims/defenses tracker — elements mapping, evidence linking, viability scoring | HIGH |

**Deliverable:** Full case management with automated state tracking, deadline management, and structured data for all 22 extraction sections

---

## Phase 4: Document Generation (Week 6-8)
**Goal:** Court-ready document production

| Task | Description | Priority |
|------|-------------|----------|
| 4.1 | Build .docx rendering engine — court-formatted documents with proper captions, fonts, margins | CRITICAL |
| 4.2 | Build PDF generation pipeline — for filings, memos, and work product | HIGH |
| 4.3 | Build court-specific format profiles — federal, each state court system, local rules | HIGH |
| 4.4 | Build template library — motions, pleadings, discovery, correspondence templates per jurisdiction | HIGH |
| 4.5 | Build watermark/marking system — DRAFT/WORK PRODUCT/CONFIDENTIAL headers per Amendment XIX | MEDIUM |
| 4.6 | Build file naming convention enforcement — `YYYY-MM-DD — [Type] — [Description].[ext]` | MEDIUM |

**Deliverable:** System produces downloadable, court-formatted .docx/.pdf files for all litigation documents

---

## Phase 5: Integration & Connectors (Week 7-9)
**Goal:** Wire external services per Amendment 1.0

| Task | Description | Priority |
|------|-------------|----------|
| 5.1 | Google Drive connector — matter file organization, document search, work product storage | HIGH |
| 5.2 | Calendar connector — deadline events with multi-tier reminders (14/7/3 day) | HIGH |
| 5.3 | Asana connector — litigation project management with phase sections (already exists in REPO — upgrade) | HIGH |
| 5.4 | Gmail connector — draft composition, prior communication search | MEDIUM |
| 5.5 | Slack connector — status updates, context retrieval | MEDIUM |
| 5.6 | PACER/CM-ECF connector — federal court docket access, filing retrieval | HIGH |
| 5.7 | State court portal connectors — e-filing status, docket search | MEDIUM |
| 5.8 | Integration testing suite — verify all connectors per Amendment XX | HIGH |

**Deliverable:** All external tool integrations functional and tested

---

## Phase 6: Pro Se Value-Add Features (Week 8-10)
**Goal:** Features that give pro se litigants advantages typically reserved for attorneys

| Task | Description | Priority |
|------|-------------|----------|
| 6.1 | **Plain Language Translator** — every legal document and concept explained in clear, simple English alongside the formal legal version | HIGH |
| 6.2 | **Filing Checklist Generator** — step-by-step instructions for physically filing documents in each court (where to go, what to bring, how many copies, how to serve) | HIGH |
| 6.3 | **Judge Profile Engine** — aggregate publicly available judicial data (prior rulings, tendencies, sentencing patterns from CourtListener) | HIGH |
| 6.4 | **Fee Waiver Assistant** — IFP (In Forma Pauperis) application guidance with income qualification check and form generation | HIGH |
| 6.5 | **Self-Represented Litigant Resources** — curated links to free legal aid, pro bono programs, law libraries, court self-help centers per jurisdiction | MEDIUM |
| 6.6 | **Courtroom Procedure Coach** — what to expect at each hearing type, how to address the judge, courtroom etiquette, objection basics | MEDIUM |
| 6.7 | **Service of Process Guide** — step-by-step service instructions per jurisdiction with approved methods, sheriffs' offices, process server databases | MEDIUM |
| 6.8 | **Form Finder** — locate and pre-fill court-specific forms (many courts have mandatory forms for pro se filers) | HIGH |
| 6.9 | **Legal Aid Eligibility Screener** — check qualification for LSC-funded legal aid, pro bono panels, law school clinics | MEDIUM |
| 6.10 | **Opposing Party Public Records Search** — business entity search (Secretary of State), property records, UCC filings, court records for prior litigation | HIGH |

**Deliverable:** Pro se-specific features that level the playing field

---

## Phase 7: Hardening & Verification (Week 9-11)
**Goal:** Ensure system reliability and accuracy

| Task | Description | Priority |
|------|-------------|----------|
| 7.1 | End-to-end test with real case scenarios (anonymized) — full lifecycle from intake to motion drafting | CRITICAL |
| 7.2 | Citation accuracy audit — verify 100% of citations in test outputs against CourtListener/Google Scholar | CRITICAL |
| 7.3 | Deadline computation testing — verify against known court calendars and computation examples | CRITICAL |
| 7.4 | Red Team stress test — have Agent 4 attack every output and verify all weaknesses are flagged | HIGH |
| 7.5 | Jurisdictional coverage testing — verify rules engine for top 10 states + federal | HIGH |
| 7.6 | WDC calibration — tune debate weights and thresholds based on test case quality metrics | HIGH |
| 7.7 | Error Museum — document every bug and edge case found during testing with root cause and fix | HIGH |
| 7.8 | User acceptance testing — real pro se user workflows | HIGH |

**Deliverable:** Verified, tested system with documented error museum and calibrated debate thresholds

---

# PART 5: VALUE-ADD CONNECTORS & DATA SOURCES

## Free / Low-Cost Legal Data APIs

| Service | What It Provides | Cost | Integration Value |
|---------|-----------------|------|-------------------|
| **CourtListener API** | 8M+ court opinions, RECAP federal docket archive, oral arguments | Free | PRIMARY case law source — verified, structured, searchable |
| **RECAP Extension/API** | Federal court (PACER) documents, dockets | Free | PACER documents without per-page fees |
| **US Code (uscode.house.gov)** | Complete United States Code in XML | Free | Full federal statutory text, section-level granularity |
| **eCFR (ecfr.gov/api)** | Code of Federal Regulations | Free | Federal regulations, updated daily |
| **Congress.gov API** | Bills, amendments, legislative history | Free | Track pending legislation affecting active cases |
| **Federal Register API** | Proposed and final rules | Free | Regulatory changes that impact cases |
| **Google Scholar** | Case law + academic legal papers | Free | Backup citation verification, legal scholarship |
| **SEC EDGAR API** | Corporate filings, 10-K, 8-K, proxy statements | Free | Business entity research, financial data for corporate defendants |
| **USPTO API** | Patent, trademark data | Free | IP litigation support |
| **FOIA.gov** | FOIA request tracking | Free | Government transparency requests |
| **State SOS APIs** | Business entity search | Free (most states) | Verify corporate status, registered agents, officers |
| **County recorder sites** | Property records, liens, UCC filings | Free-$5/search | Asset discovery, lien research |
| **PACER** | Federal court filings | $0.10/page (capped $3/doc) | Primary federal court records |

## Additional Value-Add Integrations

| Integration | Purpose | Pro Se Benefit |
|-------------|---------|----------------|
| **Court e-filing portals** | Direct filing status checks | Know instantly if your filing was accepted/rejected |
| **Zillow/Redfin API** | Property value estimates | Damages quantification, asset discovery |
| **OpenCorporates** | Global company data | Identify parent companies, subsidiaries, officers |
| **Google Maps/Geocoding** | Venue analysis, distance calculations | Service of process planning, venue convenience arguments |
| **Wolfram Alpha** | Complex calculations | Damages computation, interest calculations, present value |
| **IRS Free File** | Tax-related calculations | Tax dispute support, income verification |
| **Consumer Financial Protection Bureau (CFPB)** | Complaint database | Pattern evidence for consumer protection cases |
| **OSHA API** | Workplace safety records | Employment law, workplace injury cases |
| **EPA Enforcement API** | Environmental violation records | Environmental law cases |
| **EEOC charge data** | Employment discrimination statistics | Employment discrimination cases |

---

# PART 6: CRITICAL SAFEGUARDS FOR PRO SE LITIGANTS

## Mandatory Disclaimers (System-Level, Non-Negotiable)

1. **"This system is an AI tool, not an attorney. It does not create an attorney-client relationship. Its output is not legal advice."** — Displayed at every session start and on every deliverable.

2. **"AI-generated legal citations may be incorrect. ALWAYS verify citations through Westlaw, Lexis, Google Scholar, or court records before filing any document with a court."** — Attached to every citation.

3. **"Communications with AI systems are generally NOT protected by attorney-client privilege. Exercise caution about what information you share."** — Per Amendment XIX.B.

4. **"Deadlines computed by this system should be independently verified against court rules and calendars. Missing a court deadline can result in dismissal, default judgment, or sanctions."** — Attached to every deadline computation.

5. **"This system cannot appear in court, sign documents, or file on your behalf. You are responsible for all filings, appearances, and representations made to any court."**

## Safety Gates

| Gate | What It Prevents | How |
|------|-----------------|-----|
| Citation Verification Loop | Filing fabricated case law | Every citation must pass 5-step verification or be flagged [UNVERIFIED] |
| Deadline Conservative Computation | Missing deadlines | Always uses earlier date when ambiguous; triple-checks computation |
| Compliance Agent Veto | Procedural violations | Agent 5 can block any output that violates procedural rules |
| WDC Consensus Requirement | Low-quality output | No substantive output reaches user without passing debate |
| Confidence Flagging | Over-reliance on uncertain info | High/Moderate/Low flags on every legal assertion |
| Statute Amendment Check | Relying on outdated law | Web search verification of every statute before relying on it |
| Cross-Reference Mandate | Contradictory analysis | Red Team checks every output against prior case analysis |
| Full Extraction on Demand | Data loss between sessions | 22-section extraction runs automatically at configurable intervals |

---

# PART 7: IMPLEMENTATION TIMELINE SUMMARY

```
PHASE 0 ████████░░░░░░░░░░░░░░  Foundation (Wk 1-2)
PHASE 1 ░░░░████████████░░░░░░  Agent Core (Wk 3-5)
PHASE 2 ░░░░░░████████████░░░░  Legal Knowledge (Wk 4-6, parallel)
PHASE 3 ░░░░░░░░░░████████░░░░  Case Management (Wk 5-7)
PHASE 4 ░░░░░░░░░░░░████████░░  Doc Generation (Wk 6-8)
PHASE 5 ░░░░░░░░░░░░░░████████  Integrations (Wk 7-9)
PHASE 6 ░░░░░░░░░░░░░░░░██████  Pro Se Features (Wk 8-10)
PHASE 7 ░░░░░░░░░░░░░░░░░░████  Hardening (Wk 9-11)
```

**Phases 1-2 run in parallel. Phases 3-5 overlap. Phases 6-7 overlap.**
**Total estimated build: ~11 weeks with parallel execution.**

---

# PART 8: TECHNOLOGY STACK

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **AI Engine** | 5x Claude Opus 4.6 (1M context) | Maximum reasoning capability, full document ingestion, no context truncation |
| **Orchestration** | Claude Code CLI + custom Python orchestrator | Manages agent lifecycle, debate protocol, message routing |
| **Data Store** | SQLite (local) → PostgreSQL (if multi-tenant) | Case data, VAR, jurisdiction rules, debate logs |
| **Document Rendering** | python-docx + fpdf2 | Court-formatted .docx and .pdf generation |
| **Legal APIs** | CourtListener, US Code, eCFR, Google Scholar, PACER | Verified legal authority, case law, statutes, regulations |
| **File Storage** | Local filesystem + optional Google Drive | Matter files, work product, evidence |
| **Task Management** | Asana (existing connector) | Litigation project tracking, deadline management |
| **Calendar** | Google Calendar API | Deadline reminders, hearing dates |
| **Communication** | Gmail API + Slack API | Correspondence drafting, team updates |
| **CLI** | Existing ciphergy.sh (upgraded) | All system operations through single command interface |
| **Dashboard** | Existing Flask dashboard (upgraded) | Visual case status, deadline monitoring, debate audit logs |

---

*This roadmap is a living document. Each phase will produce a SPEC.md before implementation begins per @M:017.*

***The mission: give every pro se litigant access to the same analytical depth, strategic rigor, and procedural precision that a top litigation firm provides — with five AI minds working in concert, debating every output, verifying every citation, and catching every procedural trap before it becomes a catastrophe.***
