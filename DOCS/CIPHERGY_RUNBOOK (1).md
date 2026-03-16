# CIPHERGY — FULL PLATFORM RUNBOOK

## Dual-Environment AI Orchestration + Domain-Specific Intelligence

**CONFIDENTIAL — PRO SE WORK PRODUCT**
**Version 1.0 — March 7, 2026**
**Author:** Bo Pennington
**Domains:** ciphergy.com | ciphergy.ai | ciphergy.io

---

## Table of Contents

1. [Origin & Naming](#1-origin--naming)
2. [What Ciphergy Is](#2-what-ciphergy-is)
3. [The Three Layers](#3-the-three-layers)
4. [Layer 1: DualAI — The Infrastructure](#4-layer-1-dualai--the-infrastructure)
5. [Layer 2: Domain Intelligence — The Brain](#5-layer-2-domain-intelligence--the-brain)
6. [Layer 3: Total Extraction — The Onramp](#6-layer-3-total-extraction--the-onramp)
7. [Core Capabilities](#7-core-capabilities)
8. [Connector & Integration Architecture](#8-connector--integration-architecture)
9. [Data Sources & APIs](#9-data-sources--apis)
10. [The User Experience — How It Actually Works](#10-the-user-experience--how-it-actually-works)
11. [Legal Domain: Complete Feature Set](#11-legal-domain-complete-feature-set)
12. [Construction & Development Domain](#12-construction--development-domain)
13. [General Business Domain](#13-general-business-domain)
14. [Skills Library](#14-skills-library)
15. [Agent Architecture](#15-agent-architecture)
16. [Technical Requirements](#16-technical-requirements)
17. [File & Folder Standards](#17-file--folder-standards)
18. [Security, Confidentiality & Work Product](#18-security-confidentiality--work-product)
19. [Roadmap & Future Capabilities](#19-roadmap--future-capabilities)
20. [Appendix: Legacy Evolution](#20-appendix-legacy-evolution)

---

## 1. Origin & Naming

**Cipher** — Bo named the Claude.ai environment "Cipher" on March 7, 2026. The origin is twofold: glacier mode ("zero" — cold, concise, no emotion, the operating principle for all litigation output) and the deeper meaning of a cipher as a key that turns noise into signal. Every conversation, every document, every data point is noise until the system decodes it into actionable intelligence.

**Ciphergy** — Cipher + Energy. The platform name. The insight was that a cipher alone is static — it decodes but doesn't act. Energy is the execution layer. Ciphergy decodes *and* moves. It turns noise into signal and signal into action.

The name was born during the same period Bo was building the dual-environment AI system for active civil litigation — a system that required two AI instances running in parallel, communicating asynchronously, maintaining synchronized state, and producing court-ready documents under extreme procedural pressure. That system became the first deployment of what is now Ciphergy.

---

## 2. What Ciphergy Is

Ciphergy is a framework for running multiple AI environments as specialized parallel workers on complex, high-stakes projects — connected through shared project management tools, synchronized through version-controlled file pipelines, and governed by domain-specific behavioral rules.

It is not a single product. It is a system architecture that sits on top of existing AI tools (Claude Code, Claude.ai, Asana, Gmail, Google Drive, Slack, and others) and transforms them from isolated point solutions into a coordinated intelligence network.

The human operator sits at the center — not as a bottleneck, but as a decision-maker and physical router. The system handles all logistics: what changed, what's stale, what needs to move, what needs attention, what's next. The human decides and moves.

**What Ciphergy replaces:**
- Manual copy-paste between AI sessions
- Mental tracking of which AI knows what
- Unstructured prompt engineering for complex multi-phase projects
- Siloed tool usage (Asana for tasks, Claude for drafting, Gmail for comms — never talking to each other)
- Expensive professional services for domains where the knowledge is systematizable (legal research, compliance, document drafting, project management)

**What Ciphergy does NOT replace:**
- Licensed professional judgment (lawyers, doctors, engineers make the final call)
- Human relationships and negotiation
- Physical actions (filing documents, serving papers, attending hearings)
- Professional ethics obligations

---

## 3. The Three Layers

Ciphergy has three functional layers, each independently useful but designed to work together:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: TOTAL EXTRACTION (The Onramp)                     │
│  Universal data mining from any AI session, document, or    │
│  conversation into structured, importable knowledge         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: DOMAIN INTELLIGENCE (The Brain)                   │
│  Multi-agent personas, behavioral rules, tool directives,   │
│  practice-area expertise, stress-testing protocols          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: DUALAI (The Infrastructure)                       │
│  Dual-environment orchestration, Asana comm channel,        │
│  version control, sync pipeline, CLI tools                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Layer 1: DualAI — The Infrastructure

DualAI is the orchestration pattern that makes everything else possible. It connects two Claude environments (Claude Code and Claude.ai Desktop) through Asana as a communication bridge and a version-controlled sync pipeline.

### The Two Environments

**Claude Code (The Engine Room)**
- Opus 4.6, local terminal
- Full read/write to local filesystem (700+ files)
- 20 parallel agents, 1M+ context window
- Runs: version cascades, evidence monitoring, file management, infrastructure automation, shell scripts
- Governed by: CLAUDE.md, AGENTS.md, GUARDRAILS.md, HOOKS.md

**Claude.ai Desktop (The War Room)**
- Opus 4.6, web/desktop chat interface
- ~35 project knowledge files, 8-slot persistent memory, past conversation search
- Full document creation skills (docx, pdf, xlsx, pptx)
- Web search, MCP integrations
- Runs: strategy, drafting, legal research, communication, stress-testing
- Governed by: Custom Instructions, system memory, project knowledge

### The Asana Communication Channel

Two Asana tasks serve as unidirectional message channels:
- **CLAUDE CODE task** — Claude Code writes, Claude.ai reads
- **CLAUDE PROJECT task** — Claude.ai writes, Claude Code reads

Structured message format with type (SYNC, REQUEST, ALERT, REPORT, QUESTION, ACK), priority (CRITICAL, HIGH, MEDIUM, LOW), and status tracking (OPEN, ACKNOWLEDGED, RESOLVED). Messages persist across session boundaries — a request posted at 2 AM gets processed the next time that environment starts up.

### The Version Control System

Four files govern all state:
- **VERSION_REGISTRY.json** — Single source of truth for file versions, statuses, hashes, and the 35-file monitored list
- **VERSION_RULES.yaml** — 7 cascade triggers with rules and a final_step sync check
- **VERSION_CONTROL.md** — Human-readable protocol
- **scripts/auto_version.sh** — CLI with 8 commands (status, check, hash, sync-check, mark-synced, project-status, project-push, new-evidence)

### The Sync Pipeline

```
TRIGGER → CASCADE → SYNC-CHECK → PROJECT-PUSH → ASANA ALERT → HUMAN UPLOADS → MARK-SYNCED
```

A physical sync folder (`claude_project_<date>/`) produces drag-and-drop-ready file sets. Baseline (`v1/`) contains all 35 files. Each subsequent version folder contains ONLY the changed files. The human opens the new folder, uploads those files to Claude.ai, runs `mark-synced`. Done.

---

## 5. Layer 2: Domain Intelligence — The Brain

This is where Ciphergy becomes more than infrastructure. Layer 2 defines *how* the AI thinks about specific domains — what rules it follows, what agents it deploys, what tools it uses, how it verifies its own work, and what standards it applies to output.

### Multi-Agent Architecture

Three personas operate within Claude Code, each with a defined decision weight:

| Agent | Weight | Role |
|-------|--------|------|
| **The Strategist** | 40% | Evaluates whether output advances the project, preserves future options, maintains operational discipline |
| **The Red Team** | 35% | Attacks every output as the adversary would — finds admissions, errors, fabricated citations, unsupported claims |
| **The Bench** | 25% | Evaluates procedural compliance, credibility, and how a neutral decision-maker would receive the output |

These agents run a Weighted Debate Consensus (WDC) on every major output, producing a matrix of GREEN LIGHTS (safe), YELLOW LIGHTS (risks), and RED LIGHTS (fatal flaws).

### Behavioral Governance

**Glacier Mode** — All litigation-facing output is concise, cold, factual. No emotion, no rhetoric, no narrative flair. Every sentence serves a legal element. Less is more.

**Amateur Tell Detection** — Automated scanning for language that signals pro se, emotional, or unsophisticated posture: clichés ("govern yourselves accordingly"), emotional framing ("devastating," "heartbreaking"), over-explanation, empty threats, TV-lawyer phrasing. Replaced with sterile, statutory precision.

**Cross-Contamination Prohibition** — Parallel matters never mix in output without explicit user confirmation.

**Three Moves Ahead** — Every recommendation includes: (1) opposing counsel's likely response, (2) the court's likely reaction, (3) what exposure the action creates.

### Tool Integration Directives (from Legal CoCounsel Amendment 1.0)

**Web Search — Mandatory Verification Protocol:**
- Every case citation verified via web search before presentation; unverified citations flagged
- Current statute text searched rather than relying on training data
- Filing fees, e-filing URLs, and local rules verified against court websites
- Minimum 3 searches with varied queries for complex legal questions

**Google Drive Integration:**
- On matter intake, search Drive for existing related documents
- When user references a document by name, search Drive before asking for upload
- Advise on folder organization for the matter

**Calendar Integration:**
- Every identified deadline offered as a calendar event with 14/7/3-day reminders
- Deadline computation using correct jurisdiction's rules (excluding weekends/holidays)
- Litigation calendar generated for newly identified matters

**Asana Integration:**
- Active matter litigation project with phase-based sections
- Action items created with due dates, priorities, and descriptions
- Discovery obligations tracked as tasks
- Opposing party deadlines monitored

**Gmail Integration:**
- Demand letters and correspondence drafted directly through Gmail
- Prior communications searched to locate relevant threads
- No email sent without explicit user confirmation

**Slack Integration:**
- Context search when user references conversations or decisions
- Status updates posted to designated channels for team projects

### Evidence Confidence Monitoring

Every legal element of every count is scored on evidence strength (0-100%). Scores update when new evidence arrives, questions are answered, or discovery produces documents. Claims crossing the 75% threshold trigger RED ALERTS that persist until the user confirms them.

### Error Correction & Self-Audit

**Confidence Flagging:**
- High confidence: no flag
- Moderate confidence: "[Verify: this rule may have been amended or may differ in your jurisdiction.]"
- Low confidence: "[UNVERIFIED — research this point before relying on it.]"

**Citation Audit:** Every citation checked for existence, correct format, accurate holding attribution, current good law status, and current statute version.

---

## 6. Layer 3: Total Extraction — The Onramp

The Total Case Extraction Prompt is a universal data mining directive designed to be pasted into ANY existing AI session (Claude, GPT, Gemini, Cursor, any LLM) to produce a complete, structured export of everything that session knows about a matter.

### What It Extracts (22 Sections)

1. **Executive Case Summary** — Full narrative for a new reader
2. **Parties & Entities** — Every person, entity, attorney, court, expert, witness
3. **Complete Chronological Timeline** — Every date mentioned, strict chronological order
4. **Claims Analysis** — Every claim pursued, considered, or potential — elements, evidence, gaps, viability
5. **Defenses & Opposition Analysis** — Known defenses, counterclaims, opposing strategy
6. **Stress Testing & Risk Analysis** — Weaknesses, opposing counsel simulation, judicial reception
7. **Evidence Inventory** — Documentary, testimonial, physical, digital, expert, adverse
8. **Discovery Status** — Sent, received, disputes, strategy
9. **Motions & Court Proceedings** — Filed, pending, planned, hearings, orders
10. **Legal Research & Authorities** — Statutes, case law, rules, secondary sources, unverified citations
11. **Documents Drafted** — Complete inventory of work product
12. **Strategy & Tactical Analysis** — Overall, phase-by-phase, settlement, damages, enforcement
13. **Communications Log** — Every communication referenced
14. **Financial Analysis** — Damages, costs, opposing financials, cost-benefit
15. **Jurisdictional & Procedural Framework** — Jurisdiction, venue, rules, deadlines
16. **Insurance Analysis** — Client and opposing party coverage
17. **Open Questions** — Every unresolved issue
18. **Action Items** — Every task with responsible party, deadline, status
19. **Lessons Learned** — Strategic observations and warnings
20. **Raw Data Dump** — Final sweep for anything missed
21. **Verification Checklist** — Completeness audit
22. **Transfer Readiness Assessment** — Completeness rating by category

### Why It Matters

AI sessions are disposable. Context windows clear. Conversations disappear. Without extraction, months of legal research, strategic analysis, and document development vanish when a session ends or a platform changes. The Total Extraction Prompt captures everything in a format that can be immediately imported into a new Ciphergy environment — or any other system.

It also solves the multi-platform problem. If legal work started in GPT, moved to Gemini for research, and is now in Claude for drafting, each platform has fragments of the complete picture. Running Total Extraction on each session and combining the outputs produces a unified, deduplicated knowledge base.

---

## 7. Core Capabilities

### What Ciphergy Can Do Today

**Document Production:**
- Court filings (complaints, motions, briefs, affidavits) in jurisdiction-specific format
- Professional Word documents with full formatting control
- PDFs, spreadsheets, presentations
- Demand letters, pre-suit notices, settlement communications
- Bar complaints, regulatory filings

**Legal Analysis:**
- Element-by-element claim analysis with evidence mapping
- Opposing counsel simulation and stress testing
- Weighted Debate Consensus (multi-agent review)
- Evidence confidence scoring with threshold alerts
- Damages architecture with overlap analysis
- Citation verification via web search
- Jurisdictional quick-reference cards
- Statute of limitations watchdog

**Project Management:**
- Asana-integrated task tracking with phase-based sections
- Deadline computation with jurisdiction-specific rules
- Automated calendar events with tiered reminders
- Version control across all case documents
- Discovery obligation tracking

**Communication:**
- Glacier mode correspondence drafting
- Gmail integration for sending (with mandatory user confirmation)
- Communication log maintenance with admissibility analysis
- Slack integration for team updates

**Research:**
- Web search with mandatory verification protocol
- Statute lookup with current text and URLs
- Case law research with verification flagging
- Local rule and filing fee verification
- Multi-query synthesis for complex questions

**Infrastructure:**
- Dual-environment orchestration
- Asynchronous inter-agent communication
- Automated sync detection and delta file delivery
- CLI tools for integrity verification and sync management
- Zero-deletion archive policy

---

## 8. Connector & Integration Architecture

### Currently Connected

| Connector | Access Method | Primary Use |
|-----------|-------------|-------------|
| **Asana** | MCP (both environments) | Inter-agent comm, task management, deadline tracking |
| **Gmail** | MCP (Claude.ai) | Correspondence drafting, communication search |
| **Slack** | MCP (Claude.ai) | Context search, team updates |
| **Google Drive** | MCP (Claude.ai) | Document search, file organization |
| **Web Search** | Native (both) | Citation verification, statute lookup, current information |

### Recommended Additional Connectors

| Connector | Why | Use Case |
|-----------|-----|----------|
| **Google Calendar** | Deadline management with automated reminders | Create events for every filing deadline, response window, hearing date |
| **Figma** | Visual mockups for presentations and exhibits | Trial exhibits, demonstrative evidence, timeline visuals |
| **Vercel** | Web-based dashboards and client portals | Case status dashboards, evidence galleries, timeline viewers |
| **S&P Global / Kensho** | Financial data for damages quantification | Corporate defendant financials, asset analysis, collectability |

### Potential Future Connectors

| Connector | Why |
|-----------|-----|
| **Westlaw / Lexis** | Authoritative citation verification, KeyCite/Shepard's |
| **PACER / ECF** | Federal court e-filing and docket monitoring |
| **Florida Courts E-Filing Portal** | State court filing automation |
| **DBPR Portal** | License verification, complaint status monitoring |
| **County Property Appraiser** | Real property records, ownership history, liens |
| **Florida Secretary of State (Sunbiz)** | Entity searches, registered agent lookups |
| **DocuSign / PandaDoc** | Document execution and signature tracking |
| **Twilio** | SMS notifications for deadline alerts |
| **Stripe** | Payment tracking for settlement proceeds |
| **QuickBooks / Xero** | Financial record integration for damages quantification |

---

## 9. Data Sources & APIs

### Legal Research

| Source | URL | Use |
|--------|-----|-----|
| Florida Senate Statutes | flsenate.gov/Laws/Statutes | Current statute text |
| Google Scholar | scholar.google.com | Case law search |
| Municode | municode.com | Local ordinances |
| Florida Bar | floridabar.org | Attorney lookup, bar complaint portal |
| DBPR | myfloridalicense.com | License verification |
| Volusia County Clerk | clerk.org | Case search, recording |
| Florida Courts E-Filing | myflcourtaccess.com | E-filing portal |
| Volusia County Property Appraiser | vcpa.vcgov.org | Property records |
| Florida Ethics | disclosure.floridaethics.gov | Form 1 filing |

### Public Records

| Source | Use |
|--------|-----|
| County property records | Ownership, liens, transfers, valuations |
| Secretary of State (Sunbiz) | LLC/Corp records, registered agents |
| DBPR public records | Contractor licenses, complaints, disciplinary history |
| Court dockets | Case status, filings, orders |
| OSHA records | Construction safety violations |

### Financial

| Source | Use |
|--------|-----|
| SEC EDGAR | Corporate filings for institutional defendants |
| County tax records | Property valuations for asset analysis |
| UCC filings | Secured interests in personal property |
| Judgment lien records | Pre-existing judgments against defendants |

---

## 10. The User Experience — How It Actually Works

### Day-to-Day Workflow

**Morning: Check the Dashboard**
1. Open Asana — scan for any new tasks, upcoming deadlines, or alerts
2. If a new `vN/` folder appeared overnight (Claude Code ran a cascade), open it, upload the changed files to Claude.ai project knowledge, run `mark-synced`
3. Open Claude.ai — start working on whatever is next (drafting, analysis, research)

**Working Session in Claude.ai (The War Room):**
- Strategic analysis: "Should we add a conspiracy count?" → Claude.ai searches project knowledge, analyzes legal standards, recommends
- Document drafting: "Draft the First Amended Complaint" → Claude.ai creates .docx in Pennington Standard format
- Communication drafting: "Draft a response to this email from opposing counsel" → Three-part analysis (legal translation, strategic read, recommended response) in glacier mode
- Stress testing: "Run the WDC on the April 4 package" → Strategist, Red Team, and Bench personas simulate attack/defense/judicial review

**Working Session in Claude Code (The Engine Room):**
- Evidence processing: "I got a witness declaration from Mike" → Cascade fires, confidence scores update, red alerts check, sync pipeline runs
- File management: "Clean up the evidence folder" → Claude Code reorganizes, updates registry, posts sync notification
- Infrastructure: "Run sync-check" → CLI shows which files are stale, what needs uploading
- Bulk operations: "Update all affidavit case numbers" → Claude Code edits 3 documents, increments version, cascades

**When Something Changes:**
1. Change happens in Claude Code (new evidence, answered question, file edit)
2. CASCADE fires automatically — updates all affected files
3. SYNC-CHECK identifies which of the 35 monitored files changed
4. PROJECT-PUSH creates a new version folder with only the changed files
5. ASANA NOTIFICATION posted
6. Human opens folder, drags files to Claude.ai, runs `mark-synced`
7. Both environments are current

### The Three Human Actions

The system is designed so the human's physical role is reduced to:
1. **Drag files** — From sync folder to Claude.ai project knowledge
2. **Paste output** — Copy Claude Code output into Claude.ai (or vice versa) when direct context transfer is needed
3. **Confirm decisions** — Both environments surface questions and recommendations; the human makes the call

---

## 11. Legal Domain: Complete Feature Set

### Practice Area Coverage

**Currently Active (Pennington v. Campenni):**
- Florida common law torts (defamation per se, IIED, tortious interference)
- Florida statutory torts (civil theft § 772.11, elder exploitation § 415.1111)
- Florida civil procedure (pre-suit demands, punitive damages § 768.72, amendment as of right)
- Florida Bar Rules of Professional Conduct (conflict disqualification)
- Federal diversity jurisdiction (28 U.S.C. § 1332) as strategic lever

**Supported via CoCounsel Amendment 1.0:**
- Contract disputes and commercial litigation
- Real estate, construction, and property disputes
- Employment and labor disputes
- Consumer protection and fraud
- Family law (custody, support, property division)
- Intellectual property (trademark, copyright, trade secret, patent basics)
- Tax disputes and IRS proceedings
- Probate, successions, and trusts
- Environmental law (CERCLA, Clean Water/Air Act)
- Immigration (civil aspects)
- Personal injury and medical malpractice
- Insurance coverage disputes and bad faith
- Bankruptcy considerations in collection strategy
- Government/administrative proceedings
- Appellate practice

### Document Types Generated

All litigation documents produced as .docx files in court-specific format:

- Verified Complaints / Petitions
- Amended Complaints (First, Second, etc.)
- Motions (punitive damages, temporary injunction, compel, dismiss, summary judgment)
- Memoranda of Law
- Evidentiary Proffer Affidavits (§ 92.525 unsworn declaration standard)
- Discovery (interrogatories, requests for production, requests for admission)
- Subpoenas
- Demand Letters / Pre-Suit Notices
- Settlement Agreements
- Bar Complaints
- Lis Pendens
- Summons
- Court Forms (cover sheets, email designation)
- Strategy Memoranda (internal)
- Research Memoranda (internal)

### Quantified Risk Assessment Framework

Every claim scored across six factors:

| Factor | Ratings |
|--------|---------|
| Legal Merit | Strong / Moderate / Weak / Frivolous |
| Evidentiary Support | Well-Documented / Partially Supported / Speculative |
| Judicial Reception | Favorable / Neutral / Unfavorable |
| Opposing Defenses | Easily Overcome / Contested / Potentially Fatal |
| Damages Potential | Substantial / Moderate / Nominal / Uncertain |
| Collectability | High / Moderate / Low / Uncollectable |

Overall assessment: Proceed with confidence / Proceed with caution / Proceed only if [condition] / Do not pursue.

### Opposing Counsel Simulation

On demand, produces:
- Full written defense memorandum from opposing perspective
- Strongest defenses ranked by success likelihood
- Likely motion sequence with timing
- Discovery targets and deposition strategy
- Settlement posture analysis with estimated authority range
- Cross-examination preparation (for and against)
- Impeachment opportunities from documents in record
- Pre-filing stress test against every major document

---

## 12. Construction & Development Domain

Bo operates as a licensed Florida CGC (CGC1515629) managing multiple LLCs across FL, MS, and LA. Ciphergy supports:

- Permit tracking and compliance monitoring
- Subcontractor management and lien waiver tracking
- § 558 notice requirements and defect claim procedures
- DBPR licensing compliance and complaint defense
- Construction lien law (§ 713) — filing, enforcement, defense, fraudulent lien claims
- Builder contract drafting and dispute analysis
- Vendor balance tracking and payment dispute resolution
- Multi-state construction operations (different lien laws, licensing requirements)
- Bank relationship management and construction loan compliance

---

## 13. General Business Domain

Beyond law and construction, Ciphergy's architecture supports:

- Multi-entity LLC management (formation, compliance, annual reports)
- Real estate development (acquisition, entitlement, disposition)
- Insurance claims and coverage analysis
- Tax planning coordination (with professional advisors)
- Business development and client relationship management
- Financial modeling and pro forma analysis
- Regulatory compliance across multiple jurisdictions

---

## 14. Skills Library

Claude.ai has access to professional document creation skills:

| Skill | Trigger | Output |
|-------|---------|--------|
| **docx** | Word documents, reports, letters, legal filings | .docx with full formatting |
| **pdf** | PDF creation, extraction, merge, split, OCR | .pdf |
| **xlsx** | Spreadsheets, data analysis, financial models | .xlsx with formulas |
| **pptx** | Presentations, pitch decks, exhibits | .pptx |
| **frontend-design** | Dashboards, web components, interactive tools | .html / .jsx |

All litigation documents use the **Pennington Standard** — a locked court filing format validated against filed Florida circuit court complaints.

---

## 15. Agent Architecture

### Claude Code Agents (.claude/agents/)

| Agent | Model | Weight | Decision Rule |
|-------|-------|--------|---------------|
| **Strategist** | claude-sonnet-4-5 | 40% | Advances strategy? Preserves options? Maintains discipline? |
| **Red Team** | claude-sonnet-4-5 | 35% | What motion would opposing counsel file? Any admissions? Citations verified? Facts supported? |
| **Bench** | claude-sonnet-4-5 | 25% | Procedurally sound? Would judge grant defense motion? Pro se plaintiff credible or overreaching? |

### Claude.ai Personas (via Custom Instructions)

Claude.ai operates in a single-thread mode but switches behavioral profiles based on context:
- **Strategic Analyst** — when evaluating legal theories, settlement calculations, or case posture
- **Document Drafter** — when producing court filings, correspondence, or work product
- **Communication Advisor** — when drafting outgoing messages or analyzing incoming communications
- **Research Assistant** — when conducting legal research or citation verification

### Evidence Monitoring Agent

An automated system in Claude Code that:
- Scores every legal element of every count (0-100%)
- Fires RED ALERTS when claims cross the 75% threshold
- Tracks building claims below threshold with projected triggers
- Updates scores when new evidence arrives, questions are answered, or discovery produces documents
- Maintains an overall case posture score

---

## 16. Technical Requirements

### Software

| Component | Version | Purpose |
|-----------|---------|---------|
| Claude Code | Opus 4.6 | Terminal-based AI engine room |
| Claude.ai Desktop | Opus 4.6 | Web/desktop AI war room (requires Pro/Team plan with Projects) |
| Asana | Any plan with API access | Communication bridge + project management |
| Bash | 4.0+ | CLI scripts |
| Python 3 | 3.8+ | JSON parsing, document processing |
| Node.js | 18+ | Document generation (docx-js) |
| pandoc | Latest | Document conversion |
| LibreOffice | Latest | PDF conversion, document rendering |
| md5sum / md5 | System default | File integrity verification |

### Accounts & Configuration

- Anthropic account with Claude Pro or Team (for Projects feature)
- Claude Code license
- Asana account with API personal access token (PAT)
- MCP connectors enabled: Asana, Gmail, Slack, Google Drive (as needed)
- Local filesystem with minimum 1GB free for repo

### Repo Structure

```
PROJECT_ROOT/
├── .claude/                    ← Agent configuration
│   ├── settings.json
│   └── agents/
│       ├── strategist.md
│       ├── red-team.md
│       └── bench.md
├── 01-NN_[FOLDERS]/            ← Numbered domain folders
├── 12_ARCHIVE/                 ← All legacy content (zero deletion)
├── claude_project_<date>/      ← Sync folder (v1/ baseline + vN/ deltas)
├── scripts/
│   └── auto_version.sh         ← CLI tools
├── CLAUDE.md                   ← Root authority (Claude Code reads first)
├── AGENTS.md                   ← Persona definitions
├── GUARDRAILS.md               ← Hard prohibitions
├── HOOKS.md                    ← Pre-output pipeline
├── CONTEXT.md                  ← Living session loader
├── ASANA_COMM_PROTOCOL.md      ← Communication rules
├── VERSION_CONTROL.md          ← Human-readable protocol
├── VERSION_REGISTRY.json       ← Single source of truth
├── VERSION_RULES.yaml          ← Cascade rules
└── PROJECT_KNOWLEDGE_SYNC_AGENT.md  ← Sync detection
```

---

## 17. File & Folder Standards

### Naming Convention

```
[CATEGORY]_[Descriptive_Name]_[version].[format]

Categories:
  PROTOCOL_  — Agent behavior files
  STRATEGY_  — Strategy and analysis
  CHRONO_    — Timeline and chronology
  FILING_    — Court documents
  EVIDENCE_  — Exhibits and evidence
  COMMS_     — Communications records
  RESEARCH_  — Legal research
  OPS_       — Operational/tracking
  STANDBY_   — Conditional deployment

Format: .md for agent-readable files. .docx only for court filings.
```

### File Output Standards

- All litigation documents → .docx in court-specific format
- Analysis memos and strategy documents → .docx or .pdf when >2 pages
- Checklists and quick-reference → markdown in chat, .pdf on request
- Every litigation document includes "DRAFT — WORK PRODUCT" header until designated final
- Chat text reserved for: explanation, discussion, Q&A, coaching, short-form analysis
- Deliverables are files — always.

---

## 18. Security, Confidentiality & Work Product

### Document Marking

- Draft litigation documents: **"DRAFT — WORK PRODUCT — NOT FOR FILING"**
- Strategy memos: **"CONFIDENTIAL — LITIGATION STRATEGY"**
- Pro se work product: **"CONFIDENTIAL — PRO SE WORK PRODUCT"**
- Final versions: clean copy with proper filing headers, draft markings removed

### Prohibited Content in Filings

- Zero AI attribution in any defendant-facing or court-facing document
- Never label documents "Attorney Work Product" (pro se cannot claim attorney-client privilege)
- No references to "Claude," "Claude Code," "Anthropic," "AI," or "Generated by" in case files

### Data Handling

- Sensitive personal information (SSNs, financial account numbers, medical records) never included in Asana tasks, calendar events, or file names
- Asana messages limited to summaries and references — no raw file contents or sensitive placeholders
- Satellite matters never cross-contaminated in any shared system

### Privilege Awareness

Communications with AI systems are generally not protected by attorney-client privilege. The system reminds users of this when discussing sensitive strategy. All output is marked as work product, not privileged communication.

---

## 19. Roadmap & Future Capabilities

### Phase 1 (Current) — Single-User Legal Litigation
- Dual-environment orchestration ✓
- Asana communication bridge ✓
- Version control and sync pipeline ✓
- Legal co-counsel with multi-agent stress testing ✓
- Evidence confidence monitoring ✓
- Total case extraction ✓

### Phase 2 — Multi-Domain Expansion
- Construction project management integration
- Multi-entity business operations support
- Financial modeling and pro forma analysis
- Client portal via Vercel deployment
- Automated deadline calendar integration

### Phase 3 — Multi-User / Team Support
- Shared sync folders with role-based access
- Multiple Claude.ai Projects for different team members
- Asana project templates for new matters
- Onboarding automation (Total Extraction → Ciphergy import)

### Phase 4 — Platform Productization
- Ciphergy.ai web interface
- Matter intake wizard
- Connector marketplace
- Template library (by practice area and jurisdiction)
- Analytics dashboard (case health, evidence gaps, deadline compliance)

### Phase 5 — Autonomous Operations
- Auto-triggered cascades without human intervention
- Automated sync (eliminating manual file upload)
- Proactive monitoring (deadline watchdog, opposing party filing alerts)
- Self-healing infrastructure (conflict detection and resolution)

---

## 20. Appendix: Legacy Evolution

### What Came Before Ciphergy

**v0.1 — Single-Chat Legal Research (Pre-March 4)**
- One Claude.ai conversation handling everything
- No persistent state, no version control
- Context lost between sessions
- Documents drafted in chat, manually copied to files

**v0.2 — Multi-Agent Legal CoCounsel System Prompt (March 4-6)**
- Structured system prompt with agent personas
- Tool integration directives (web search, Drive, Calendar, Asana, Gmail, Slack)
- Practice area coverage expansion
- Still single-environment, no orchestration

**v0.3 — DualAI Architecture (March 7)**
- Claude Code + Claude.ai running in parallel
- Asana communication bridge established
- Version control system (registry, rules, CLI)
- Sync agent and pipeline built
- Evidence confidence monitoring deployed

**v1.0 — Ciphergy (March 7, current)**
- Full integration of all three layers
- Total Case Extraction Prompt for universal onboarding
- Legal CoCounsel Amendment 1.0 for tool governance
- DualAI infrastructure for orchestration
- 35-file synced project knowledge
- 713-file versioned repo
- Clean numbered folder structure
- All systems verified and operational

### Documents That Shaped the System

| Document | Version | Role |
|----------|---------|------|
| Multi-Agentic Legal CoCounsel System Prompt | v1.0 (base) | Original agent persona definitions and practice area coverage |
| Legal CoCounsel Amendment 1.0 | v1.0 | Tool integration directives, error correction, risk assessment |
| Total Case Extraction Prompt | v1.0 | Universal data mining for session migration |
| CLAUDE.md | V2.1 | Root authority for Claude Code (incorporates Asana + version control) |
| PENNINGTON_PROJECT_INSTRUCTIONS.md | v1.0 | Custom instructions governing Claude.ai behavior |
| DualAI README | v1.0 | Technical documentation of the orchestration architecture |
| ASANA_COMM_PROTOCOL.md | v1.0 | Inter-agent communication rules |
| VERSION_CONTROL.md | v1.0 | Human-readable version control protocol |

---

**CONFIDENTIAL — PRO SE WORK PRODUCT**
**Bo Pennington / Pentek Design Build LLC**
**No portion of this document may be shared, distributed, or reproduced without express written authorization.**

---

*Ciphergy v1.0 — Built March 7, 2026*
*Cipher + Energy: Turns noise into signal. Turns signal into action.*
