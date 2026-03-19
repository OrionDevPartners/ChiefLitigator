# CIPHERGY — COMPLETE RUNBOOK

## Multi-Agentic Legal Co-Counsel Ecosystem

**Version 1.0 — March 2026**
**Classification: Master Operations Manual**

---

## TABLE OF CONTENTS

1. What Is Ciphergy
2. Mission & Vision
3. System Architecture
4. The Seven Agents
5. Core Capabilities
6. Practice Area Coverage
7. Document Library (Prompt Stack)
8. Connector Ecosystem
9. Recommended APIs & Data Sources
10. Recommended Skills & Tools
11. Operational Workflows
12. Data Extraction & Portability
13. Security, Privacy & Ethical Framework
14. Environment Setup Guide
15. Maintenance & Evolution Roadmap

---

## 1. WHAT IS CIPHERGY

Ciphergy is a **multi-agentic AI-powered legal co-counsel ecosystem** built on Claude (Anthropic) and designed to provide a pro se litigant with the full operational capability of a well-staffed litigation team. It is not a single prompt — it is an integrated system of specialized prompts, connected tools, data sources, extraction protocols, and workflow directives that work together to handle the complete lifecycle of any legal matter from pre-suit investigation through post-judgment enforcement.

Ciphergy is:

- **Jurisdiction-agnostic**: It operates in any U.S. state, any federal district, any appellate circuit, and any specialized tribunal. It does not default to any jurisdiction — it identifies the correct one on intake and adapts all terminology, rules, and analysis accordingly.

- **Multi-agentic**: It deploys seven specialized virtual agents, each operating at the level of a seasoned practitioner in its domain. These agents coordinate through a Lead Strategist to ensure all work product serves a coherent litigation narrative.

- **Tool-integrated**: It connects to external services (Google Drive, Gmail, Calendar, Asana, Slack, and more) to operate not just as an advisor, but as a functional litigation operations center — tracking deadlines, managing tasks, searching documents, drafting correspondence, and monitoring case progress.

- **Portable**: It includes a Total Case Extraction protocol that can mine 100% of case data from any AI session, sandbox, or operator and transfer it into a new Ciphergy environment with zero data loss.

- **Self-auditing**: It flags its own confidence levels, verifies citations before presenting them, corrects errors proactively, and stress-tests its own work product through an Opposing Counsel Simulation agent.

---

## 2. MISSION & VISION

### Mission

To empower any pro se litigant to prosecute or defend any civil matter with the strategic precision, procedural compliance, and analytical depth of a fully staffed litigation firm — regardless of their legal training, financial resources, or geographic location.

### Vision

A world where access to justice is not determined by ability to pay for legal representation. Ciphergy does not replace attorneys — it eliminates the knowledge gap that makes self-representation dangerous. It teaches the "why" behind every "what," drafts to court-ready standards, and keeps the user three steps ahead of the opposition.

### Core Principles

1. **Never fabricate** — Every citation is verified or flagged. Every assertion carries a confidence level.
2. **Never assume jurisdiction** — Confirm before applying any law.
3. **Never leave the user stranded** — Every analysis ends with concrete next steps, deadlines, and filing instructions.
4. **Draft for the judge** — Every document assumes an intelligent but busy reader.
5. **Think about enforcement before filing** — A judgment is worthless if uncollectable.
6. **Preserve the record** — Every recommendation considers appellate preservation.
7. **Teach, don't just do** — The user must understand why, not just what.

---

## 3. SYSTEM ARCHITECTURE

Ciphergy is assembled from four layers:

### Layer 1: Prompt Stack (The Brain)

The core operating instructions that govern all AI behavior within the system:

| Document | Purpose | Format |
|---|---|---|
| **Base Prompt v1.0** | Core identity, agent definitions, operating principles, subject matter coverage, communication standards, ethical boundaries, standing instructions | .md / .docx |
| **Amendment 1.0** | Tool usage directives, document processing protocol, deadline management, expanded practice areas, error correction, risk assessment framework, opposing counsel simulation enhancements, file organization, confidentiality protections | .md / .pdf |
| **Total Case Extraction Prompt** | 22-section zero-loss data mining protocol for transferring case data between systems | .md / .docx |
| **This Runbook** | Master reference for the entire ecosystem | .md / .docx |

### Layer 2: Connected Tools (The Hands)

External services that give Ciphergy the ability to act — not just advise:

- **Google Drive** — Case file repository, document search, version comparison
- **Gmail** — Correspondence search, demand letter drafting, communication tracking
- **Google Calendar** — Deadline tracking, hearing dates, multi-reminder alerts
- **Asana** — Litigation task management by phase, discovery tracking, action items
- **Slack** — Team coordination, context search, status updates
- **Web Search** — Citation verification, current statute research, court information
- **Figma** — Visual timelines, case diagrams, relationship maps
- **S&P Global** — Corporate research, financial analysis, damages data
- **Zapier** — Bridge to 8,000+ apps, PACER alert routing, workflow automation
- **DocuSign** — Settlement agreement execution, contract tracking
- **Notion** — Legal knowledge base, research memo repository
- **Airtable** — Structured databases for evidence, witnesses, exhibits

### Layer 3: Data Sources (The Knowledge)

Where Ciphergy gets its legal intelligence:

- **Web search** (primary verification layer for all citations and current law)
- **Google Scholar** (case law, academic legal analysis)
- **Court websites** (local rules, standing orders, e-filing portals, fee schedules)
- **State legislature websites** (current statutory text)
- **Cornell LII** (federal statutes, regulations, constitutional text)
- **PACER** (federal court filings — accessed manually with guidance)
- **State court e-filing systems** (accessed manually with guidance)
- **Secretary of State websites** (entity searches, registered agents)
- **County recorder/assessor sites** (property records, liens, conveyance records)
- **S&P Global / Kensho** (financial data, corporate intelligence)
- **User-uploaded documents** (contracts, pleadings, evidence, correspondence)
- **Google Drive** (prior work product, case files, templates)

### Layer 4: Output Engine (The Deliverables)

How Ciphergy delivers work product:

- **Litigation documents** → .docx files formatted to court specifications
- **Research memos** → .docx or .pdf files
- **Analysis and strategy** → Chat-based coaching with structured frameworks
- **Timelines and diagrams** → Visual artifacts (HTML, SVG, Figma)
- **Checklists and quick-references** → Markdown or .pdf
- **Calendar events** → Google Calendar entries with multi-tier reminders
- **Task assignments** → Asana projects and tasks by litigation phase
- **Correspondence** → Gmail drafts for user review and approval

---

## 4. THE SEVEN AGENTS

Each agent is a specialized virtual persona within the system. Any response may draw on one or multiple agents depending on the task.

### Agent 1: Lead Strategist

**Domain**: Case theory, big-picture strategy, risk assessment, settlement posture, appellate preservation, inter-agent coordination.

**Activates when**: New matter intake, strategic pivots, settlement discussions, pre-trial decisions, appeal considerations.

**Delivers**: Case theory memos, strategic recommendations, risk assessments, settlement analysis, overall litigation plan.

### Agent 2: Legal Research

**Domain**: Statutory analysis, case law research, regulatory interpretation, jurisdictional surveys, authority verification.

**Activates when**: Any legal question, citation verification, jurisdictional analysis, circuit split identification.

**Delivers**: Research memos, jurisdictional surveys, annotated authority lists, statutory analysis, issue-spotting reports.

**Critical rule**: Verifies all citations via web search before presenting. Flags anything unverified.

### Agent 3: Drafting

**Domain**: All litigation document production — pleadings, motions, memoranda, discovery, affidavits, briefs, letters, orders.

**Activates when**: Any document needs to be produced.

**Delivers**: Court-ready .docx files formatted to the specific court's rules, with proper captions, certificate of service, and verification clauses.

### Agent 4: Procedural & Compliance

**Domain**: Filing requirements, service rules, deadline computation, local rules, e-filing protocols, fee schedules, standing orders.

**Activates when**: Filing a document, computing a deadline, confirming service requirements, identifying procedural traps.

**Delivers**: Filing checklists, deadline calendars, service instructions, fee calculations, e-filing guidance.

### Agent 5: Evidence & Discovery

**Domain**: Admissibility analysis, authentication, hearsay, privilege, discovery strategy, preservation, expert witness standards.

**Activates when**: Evidence assessment, discovery planning, document review, deposition preparation, trial prep.

**Delivers**: Evidence inventories, admissibility analyses, discovery packages (interrogatories, RFPs, RFAs), preservation letters, expert witness evaluations.

### Agent 6: Opposing Counsel Simulation

**Domain**: Defense anticipation, counterclaim prediction, stress testing, cross-examination preparation, weakness identification.

**Activates when**: Before any major filing, during strategy sessions, deposition preparation, trial preparation, settlement negotiation.

**Delivers**: Defense memos (from opposing perspective), anticipated motion sequences, cross-examination outlines, impeachment plans, stress-test reports.

### Agent 7: Judgment & Enforcement

**Domain**: Post-judgment collection, garnishment, liens, asset discovery, judgment domestication, execution strategy.

**Activates when**: Pre-suit collectability assessment, post-trial enforcement planning, settlement valuation.

**Delivers**: Asset search guidance, garnishment/seizure strategies, lien priority analysis, domestication roadmaps, collectability assessments.

---

## 5. CORE CAPABILITIES

### Research & Analysis
- Multi-step deep legal research with citation verification
- Jurisdictional surveys across all 50 states
- Claim viability assessments with quantified risk framework
- Conflict of law analysis
- Circuit split identification
- Statute of limitations / prescription watchdog

### Document Drafting
- Complaints, answers, motions, memoranda, briefs (trial and appellate)
- Discovery packages (interrogatories, RFPs, RFAs, subpoenas, deposition notices)
- Affidavits, declarations, proposed orders
- Demand letters, cease-and-desist letters, preservation/litigation hold letters
- Settlement communications (Rule 408 aware)
- All documents produced as formatted .docx files to court specifications

### Litigation Management
- Deadline tracking and computation (jurisdiction-specific rules)
- Task management by litigation phase (via Asana)
- Discovery obligation tracking
- Opposing party deadline monitoring
- Matter file organization (standardized folder structure)
- Communications logging

### Strategic Planning
- Case theory development and narrative construction
- Discovery strategy (offensive and defensive)
- Motion practice sequencing and timing
- Settlement negotiation and mediation preparation
- Trial preparation (witness lists, exhibit organization, examination outlines)
- Appellate issue preservation
- Post-judgment enforcement planning

### Document Analysis
- Complaint analysis (claims, elements, facts, defenses, deadlines)
- Opposing brief analysis (arguments, authority strength, counter-arguments)
- Contract review (clause-by-clause, deviation detection, compliance checking)
- Document comparison (similarities, differences, favorability)
- Deposition transcript analysis (admissions, contradictions, impeachment)
- Timeline assembly from document sets

### Evidence Management
- Complete evidence inventory with admissibility analysis
- Authentication requirement mapping
- Hearsay analysis (exceptions, exemptions, residual)
- Privilege review
- Spoliation risk assessment
- Expert witness evaluation (Daubert/Frye)

---

## 6. PRACTICE AREA COVERAGE

### Primary Practice Areas
- **Construction Law** — Liens, defects, warranties, contractor licensing, bond claims, insurance coverage
- **Real Estate Law** — Sales disputes, hidden defects, foreclosure, boundary disputes, easements, partition
- **Plaintiff's Torts** — Negligence, fraud, defamation, tortious interference, IIED/NIED, conversion, nuisance, privacy
- **Contract Law** — Formation, breach, interpretation, remedies, UCC
- **Insurance Law** — Coverage disputes, bad faith, UM/UIM, first-party/third-party
- **Business Law** — Entity disputes, operating agreements, derivative actions, veil piercing

### Extended Practice Areas (Amendment 1.0)
- **Family Law** — Divorce, custody, support, protective orders, QDROs, UCCJEA
- **Intellectual Property** — Trademark, copyright, trade secrets, patent basics, licensing
- **Tax Disputes** — IRS audit/appeals, Tax Court, state tax tribunals, innocent spouse, OIC
- **Probate & Successions** — Will contests, trust disputes, guardianship, estate administration
- **Environmental Law** — CERCLA, Clean Water/Air Act, toxic torts
- **Immigration (Civil)** — Employment authorization, Padilla, employer compliance, FOIA

### Cross-Jurisdictional Areas
- Federal civil rights (§ 1983, Bivens, qualified immunity)
- Employment law (Title VII, ADA, ADEA, wage claims, non-competes)
- Bankruptcy basics (automatic stay, proof of claim, adversary proceedings)
- Administrative law (exhaustion, licensing boards, regulatory disputes)
- ADR (arbitration, mediation, FAA, state arbitration acts)
- Judgment enforcement (domestication, garnishment, seizure, lien priority)

---

## 7. DOCUMENT LIBRARY (PROMPT STACK)

These are the documents that comprise the Ciphergy system. All should be loaded into the Claude Project instructions or provided at the start of each session:

| # | Document | File | Purpose | When to Use |
|---|---|---|---|---|
| 1 | **Base System Prompt v1.0** | Multi_Agentic_Legal_CoCounsel_System_Prompt.md | Core operating instructions for all 7 agents | Always loaded in Project instructions |
| 2 | **Amendment 1.0** | Legal_CoCounsel_Amendment_1.0.md | Tool directives, expanded capabilities, error correction, risk framework | Always loaded in Project instructions (after Base) |
| 3 | **Total Case Extraction Prompt** | Total_Case_Extraction_Prompt.md | Zero-loss data mining from any AI session | Paste into any existing session to extract all case data |
| 4 | **Connector Integration Guide** | Connector_Integration_Guide.docx | Complete connector inventory and setup | Reference during environment setup |
| 5 | **This Runbook** | Ciphergy_Runbook.md | Master reference for entire ecosystem | Reference document; does not need to be loaded into instructions |

### How to Deploy

1. Create a new Claude Project named "Ciphergy — [Matter Name]"
2. In Project Instructions, paste the **Base System Prompt v1.0** in its entirety
3. Immediately below it, paste **Amendment 1.0** in its entirety
4. Connect all Tier 1 connectors (Google Drive, Gmail, Calendar, Asana, Slack)
5. Upload relevant case documents to the Project knowledge base or Google Drive
6. Begin your first conversation with: "New matter intake. Here are the facts: [...]"

### How to Import Data from an Existing Session

1. Open the existing AI session where case work was performed
2. Paste the **Total Case Extraction Prompt** into that session
3. Let the system execute the full 22-section extraction
4. Copy the extraction output
5. Open a new Ciphergy conversation
6. Paste the extraction with the instruction: "Ingest the following case extraction and confirm receipt of all sections. Then provide your assessment of case status and recommended immediate priorities."

---

## 8. CONNECTOR ECOSYSTEM

### Tier 1 — Critical (Connect Immediately)

| Connector | Purpose in Ciphergy | Status |
|---|---|---|
| **Google Drive** | Case file repository, document search, version comparison, work product storage | MUST CONNECT |
| **Gmail** | Correspondence search, demand letter drafting, communication timeline reconstruction | CONNECTED |
| **Google Calendar** | Deadline tracking, hearing dates, prescription watchdog, multi-tier reminders | MUST CONNECT |
| **Asana** | Litigation task management by phase, discovery tracking, action items, opposing party deadlines | CONNECTED |
| **Slack** | Context search, team coordination, status updates | CONNECTED |
| **Web Search** | Citation verification, current statute research, court rules, e-filing info | BUILT-IN |

### Tier 2 — High Value (Connect This Week)

| Connector | Purpose in Ciphergy |
|---|---|
| **Notion** | Legal knowledge base, research memo repository, cross-matter reference |
| **Zapier** | Bridge to PACER alerts, court notification routing, CRM integration, 8,000+ app workflows |
| **DocuSign** | Settlement agreement execution tracking, contract signature monitoring |
| **S&P Global** | Corporate financial research, damages data, asset discovery for enforcement | CONNECTED |
| **Figma** | Litigation timelines, case relationship diagrams, evidence maps | CONNECTED |

### Tier 3 — Specialized (Connect As Needed)

| Connector | Purpose in Ciphergy |
|---|---|
| **Airtable** | Structured evidence databases, witness tracking, exhibit logs |
| **Canva** | Trial presentation graphics, exhibit boards, demonstrative evidence |
| **Harvey** | Purpose-built legal AI for specialized research (if available) |
| **LegalZoom** | Entity formation, registered agent services |
| **FactSet** | Financial research for commercial litigation and securities claims |
| **Vercel** | Deploy client-facing case status dashboards or custom legal tools | CONNECTED |
| **GitHub** | Document version control for complex matters |
| **WordPress** | Web content analysis for defamation claims, publication date evidence |

---

## 9. RECOMMENDED APIs & DATA SOURCES

### Free / Open Access Legal Data Sources

| Source | URL | What It Provides | How Ciphergy Uses It |
|---|---|---|---|
| **Google Scholar** | scholar.google.com | Case law, legal journals | Case law research and verification |
| **Cornell LII** | law.cornell.edu | Federal statutes, CFR, Constitution, UCC | Statutory text verification |
| **Congress.gov** | congress.gov | Federal legislation, bill tracking | Legislative history research |
| **GovInfo** | govinfo.gov | Federal Register, CFR, congressional reports | Regulatory research |
| **CourtListener / RECAP** | courtlistener.com | Federal court opinions, PACER data | Case law research, docket tracking |
| **State legislature sites** | [varies by state] | State statutory text | State statute verification |
| **State court websites** | [varies by state] | Local rules, standing orders, e-filing | Procedural compliance |
| **PACER** | pacer.uscourts.gov | Federal court dockets, filings | Case tracking (manual access, $0.10/page) |
| **SEC EDGAR** | sec.gov/edgar | Corporate filings, financial disclosures | Entity research, damages, enforcement |
| **SOS / Entity Search** | [varies by state] | Business entity records, registered agents | Party identification, service of process |
| **County recorder sites** | [varies by county] | Property records, liens, conveyances | Real estate claims, enforcement |
| **FOIA.gov** | foia.gov | Federal FOIA request portal | Government records for evidence |

### Paid / Subscription Legal Data Sources

| Source | What It Provides | Ciphergy's Relationship |
|---|---|---|
| **Westlaw** | Comprehensive case law, KeyCite, statutes, secondary sources | No direct integration. User must verify citations manually. Ciphergy provides exact search terms. |
| **LexisNexis** | Case law, Shepard's citations, statutes, public records | Same as Westlaw. |
| **Bloomberg Law** | Case law, dockets, analytics, transactional resources | Alternative to Westlaw/Lexis. |
| **Fastcase** | Free with many state bar memberships. Case law, statutes. | Recommend user check if included with their bar association or library card. |
| **Casetext / CoCounsel** | AI-powered legal research (Thomson Reuters) | Commercial legal AI competitor. Not integrated but user may cross-reference. |
| **Harvey** | Legal-specific AI for research, drafting, analysis | Claude connector available. Connects as Tier 2/3 tool. |
| **vLex / Vincent AI** | Global case law, litigation analytics, 850M+ court records | No direct integration. Manual cross-reference. |

### Public Records & Investigative Sources

| Source | Purpose |
|---|---|
| **County property records** | Real estate claims, asset discovery for enforcement |
| **UCC filings** (Secretary of State) | Lien searches, secured transaction verification |
| **Federal/state tax liens** | Asset encumbrance discovery |
| **Bankruptcy court records** (PACER) | Debtor status, discharge verification, preference actions |
| **Social media** (Facebook, LinkedIn, Instagram) | Evidence collection, witness identification, asset discovery |
| **News archives** | Background on parties, prior litigation, business disputes |
| **State licensing boards** | Professional license verification, disciplinary history |
| **Better Business Bureau** | Complaint history for UDAP/consumer protection claims |
| **OSHA records** | Workplace safety for employment and construction claims |
| **Building permit records** | Construction law claims, code compliance verification |
| **Insurance department filings** | Carrier financial condition, policy form filings |

---

## 10. RECOMMENDED SKILLS & TOOLS

### Claude Built-In Capabilities Used by Ciphergy

| Capability | How Ciphergy Uses It |
|---|---|
| **Web Search** | Citation verification, current law research, court information, e-filing URLs |
| **Code Execution** | Document generation (.docx, .pdf), data analysis, timeline visualization |
| **File Creation** | Producing court-ready litigation documents as downloadable files |
| **Artifacts** | Interactive timelines, case dashboards, evidence maps, checklists |
| **Deep Research** | Multi-step legal research with query refinement and synthesis |
| **Image Search** | Property photos, location verification, party identification context |
| **Places Search** | Court locations, process server offices, expert witness firms |

### External Tools & Platforms

| Tool | Category | Purpose |
|---|---|---|
| **Asana** | Project Management | Litigation phase tracking, discovery management, deadline compliance |
| **Google Workspace** | Productivity | Drive (files), Gmail (comms), Calendar (deadlines), Docs (collaboration) |
| **Notion** | Knowledge Management | Legal research wiki, case law notes, strategy library |
| **Zapier** | Automation | PACER alert routing, email-to-task workflows, cross-platform triggers |
| **DocuSign** | Document Execution | Settlement agreements, contract execution tracking |
| **Airtable** | Database | Evidence tracking, witness databases, exhibit logs, discovery matrices |
| **Figma / FigJam** | Visual Design | Case timelines, relationship maps, organizational charts |
| **Canva** | Presentation Design | Trial exhibits, hearing aids, demonstrative evidence |

---

## 11. OPERATIONAL WORKFLOWS

### Workflow 1: New Matter Intake

1. User provides facts
2. System identifies jurisdiction(s), confirms with user
3. System generates Jurisdictional Quick-Reference Card
4. System runs Claims Explorer — identifies all viable claims
5. System checks prescription/limitation for each claim
6. System generates Matter-Type Checklist for jurisdiction
7. System creates Asana project with litigation phase sections
8. System creates Calendar events for known deadlines
9. System produces Executive Case Assessment

### Workflow 2: Complaint Received (Defense)

1. User uploads complaint
2. System reads entire document (Document Processing Protocol)
3. System produces Complaint Analysis (claims, elements, facts, defenses, deadlines)
4. System computes answer deadline
5. System drafts Answer with Affirmative Defenses
6. System runs Opposing Counsel Simulation to stress-test defenses
7. System generates discovery strategy
8. System creates deadline calendar

### Workflow 3: Motion Practice

1. System researches the legal issue (3+ searches minimum)
2. System drafts Motion and Supporting Memorandum
3. System runs Opposing Counsel Simulation against the draft
4. System revises based on stress test
5. System drafts Proposed Order
6. System generates Certificate of Service
7. System provides filing instructions (where, how, fee, format)

### Workflow 4: Discovery Package

1. System analyzes claims and defenses to identify discovery needs
2. System drafts Interrogatories (tailored to elements and defenses)
3. System drafts Requests for Production
4. System drafts Requests for Admission
5. System drafts Deposition Notices (if applicable)
6. System creates discovery tracking in Asana
7. System sets response deadlines in Calendar

### Workflow 5: Trial Preparation

1. System assembles witness list with examination outlines
2. System organizes exhibit list with authentication analysis
3. System prepares motions in limine
4. System drafts proposed jury instructions
5. System generates opening and closing statement frameworks
6. System runs cross-examination preparation (Opposing Counsel Simulation)
7. System produces trial binder outline

### Workflow 6: Case Transfer (Between AI Systems)

1. Open existing session
2. Paste Total Case Extraction Prompt
3. System executes 22-section extraction
4. Copy output to new Ciphergy project
5. System ingests, confirms receipt, identifies gaps
6. System produces Transfer Readiness Assessment
7. Work continues seamlessly

---

## 12. DATA EXTRACTION & PORTABILITY

Ciphergy is designed for zero-lock-in. The Total Case Extraction Prompt extracts:

| Section | What It Captures |
|---|---|
| Executive Summary | Full case narrative sufficient for cold-start |
| Parties & Entities | Every person, entity, attorney, judge, expert, witness |
| Timeline | Every date mentioned — chronological, sourced, significance-rated |
| Claims Analysis | Element-by-element with evidence mapping, gaps, viability |
| Defenses & Opposition | Every defense, counterclaim, rebuttal, and stress test result |
| Stress Testing | Every vulnerability, simulation result, and mitigation strategy |
| Evidence Inventory | Documentary, testimonial, physical, digital, expert — with admissibility |
| Discovery Status | Sent, received, disputes, strategy — full status board |
| Motions & Proceedings | Filed, pending, planned — with rulings and impact |
| Legal Research | Every statute, case, rule, and secondary source — with verification status |
| Work Product | Every document drafted — full text or complete structure |
| Strategy | Theory, phase strategy, settlement, damages, enforcement |
| Communications | Every communication logged with significance |
| Financials | Damages, costs, opposing financials, cost-benefit |
| Jurisdiction & Procedure | Governing law, venue, rules, deadlines |
| Insurance | Both sides — coverage, limits, disputes |
| Open Questions | Everything unresolved with priority and next steps |
| Action Items | Every task with owner, deadline, status, dependencies |
| Lessons Learned | Strategic observations and warnings for next handler |
| Raw Data Dump | Everything the structured sections missed |
| Verification Checklist | 16-point quality control |
| Transfer Assessment | Completeness rating and top 5 priorities for receiving system |

---

## 13. SECURITY, PRIVACY & ETHICAL FRAMEWORK

### What Ciphergy Is Not

- Ciphergy is **not a lawyer** and does not provide legal representation
- Ciphergy is **not privileged** — AI communications are generally discoverable
- Ciphergy is **not infallible** — it self-audits, flags confidence levels, and instructs users to verify

### Ethical Boundaries

1. Never fabricate citations or legal authority
2. Never advise conduct violating rules of professional conduct, court rules, or law
3. Never send communications without explicit user confirmation
4. Never modify or delete user files without instruction
5. Always recommend attorney consultation for high-stakes matters (criminal exposure, complex class actions, imminent deadlines)
6. Always remind users about the non-privileged nature of AI communications

### Confidentiality Protections

- All draft documents marked "DRAFT — WORK PRODUCT — NOT FOR FILING"
- All strategy documents marked "CONFIDENTIAL — LITIGATION STRATEGY"
- No sensitive PII in file names, calendar events, or task titles
- Confidentiality reminder at the start of conversations involving sensitive strategy

### Error Correction Protocol

- **High Confidence**: No flag needed (verified, established, clear statutory text)
- **Moderate Confidence**: "[Verify: this rule may have been amended or may differ in your jurisdiction.]"
- **Low Confidence**: "[UNVERIFIED — research this point before relying on it.]"
- Errors acknowledged immediately, corrected with verified sources, downstream impact assessed
- System never defends incorrect positions once error is identified

---

## 14. ENVIRONMENT SETUP GUIDE

### Step-by-Step Deployment

#### Phase 1: Create the Project (5 minutes)

1. Go to claude.ai
2. Create a new Project: "Ciphergy — [Matter Name or General]"
3. In Project Instructions, paste the full text of **Base System Prompt v1.0**
4. Immediately below, paste the full text of **Amendment 1.0**
5. Upload this Runbook and the Connector Guide to Project Knowledge (reference only)

#### Phase 2: Connect Tools (10 minutes)

1. Go to claude.ai/settings/connectors
2. Connect **Google Drive** — Authorize your Google account
3. Connect **Google Calendar** — Authorize
4. Verify **Asana** is connected (already live)
5. Verify **Gmail** is connected (already live)
6. Verify **Slack** is connected (already live)
7. Verify **Figma** is connected (already live)
8. Verify **S&P Global** is connected (already live)
9. Connect **Notion** — Create a "Legal Research" workspace first
10. Connect **Zapier** — Set up PACER/court notification routing

#### Phase 3: Organize Google Drive (15 minutes)

Create the standardized folder structure:

```
Ciphergy — [Case Name]
├── 01 — Pleadings (Plaintiff / Defendant)
├── 02 — Motions (Plaintiff / Defendant)
├── 03 — Discovery (Sent / Received / Responses)
├── 04 — Depositions
├── 05 — Correspondence
├── 06 — Court Orders
├── 07 — Evidence (Documents / Photos-Video / Expert Reports)
├── 08 — Research & Memos
├── 09 — Trial Preparation
├── 10 — Settlement
└── 11 — Administrative (Deadlines / Fees / Service Records)
```

#### Phase 4: First Conversation (Immediately)

Open a new conversation in the Project and type:

> "Integration test. Confirm you can access: (1) Web search, (2) Google Drive, (3) Google Calendar, (4) Asana, (5) Gmail, (6) Slack. Report status of each."

Then:

> "New matter intake. Here are the facts: [provide your case facts]"

---

## 15. MAINTENANCE & EVOLUTION ROADMAP

### Ongoing Maintenance

- **Weekly**: Check connector status — reconnect any that have timed out
- **Per matter**: Update Asana tasks and Calendar deadlines as the case evolves
- **Per filing**: Save all filed documents to Google Drive in the correct folder with proper naming convention (YYYY-MM-DD — [Type] — [Description].ext)
- **Quarterly**: Check for new Claude connectors that may benefit the system
- **Per session**: If the conversation is getting long, use the Total Case Extraction Prompt to export and start fresh

### Planned Enhancements

| Enhancement | Description | Status |
|---|---|---|
| Westlaw/Lexis connector | Direct citation verification within Ciphergy | Awaiting third-party MCP development |
| PACER connector | Direct docket search and filing retrieval | Not yet available; use Zapier email routing as bridge |
| Court e-filing integration | File documents directly from Ciphergy | Not yet available; manual filing with Ciphergy guidance |
| Voice interface | Dictate facts and receive verbal coaching | Claude mobile app supports voice input now |
| Multi-matter dashboard | Visual overview of all active matters and deadlines | Build in Airtable + Ciphergy artifacts |
| Template library | Pre-built templates for common filings by jurisdiction | Build incrementally as matters are handled |
| Deposition transcript AI | Auto-analyze deposition transcripts on upload | Functional now via Document Processing Protocol |
| Expert witness database | Searchable database of expert witnesses by specialty and jurisdiction | Build in Notion or Airtable |

### Version History

| Version | Date | Changes |
|---|---|---|
| Base Prompt v1.0 | March 2026 | Initial release — 7 agents, 9 sections, full practice area coverage |
| Amendment 1.0 | March 2026 | Added Sections X-XX: tool directives, document processing, deadlines, expanded practice areas, error correction, risk framework, opposing counsel enhancements, file organization, confidentiality |
| Total Case Extraction v1.0 | March 2026 | 22-section zero-loss extraction protocol |
| Connector Guide v1.0 | March 2026 | Complete connector inventory with 3-tier priority system |
| Runbook v1.0 | March 2026 | This document — master reference for entire ecosystem |

---

*This runbook governs the Ciphergy ecosystem. Update it as the system evolves.*

***Ciphergy exists because access to justice should not depend on the ability to pay. Build it. Use it. Win.***
