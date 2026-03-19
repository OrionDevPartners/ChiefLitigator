# CIPHERGY — PRODUCT SPECIFICATION V2.0

## Multi-Agent AI Orchestration Platform
## Domain-Agnostic | Case-Agnostic | Model-Agnostic

**CONFIDENTIAL — Bo Pennington / Pentek Design Build LLC**
**Version 2.0 — March 15, 2026**
**Synthesized from: Deep Research Report + Claude Code Roadmap + Winning Edge Enhancements + DualAI Prototype + Legal CoCounsel Amendment 1.0 + Total Extraction Prompt**

---

## WHAT CHANGED IN V2

V1 (CIPHERGY_RUNBOOK.md) documented the working prototype — two separate Claude instances duct-taped together via Asana. V2 is the **actual product specification** for ciphergy.ai: a native multi-agent platform where agents share one environment, communicate directly, and orchestrate dynamically.

Key additions from deep research and Claude Code roadmap:
- 5-agent legal architecture with Compliance veto (from Claude Code)
- 12 winning-edge enhancements integrated into agent capabilities (from Claude Code)
- Supervisor orchestration pattern validated by Google DeepMind research
- MCP-first integration strategy (1,200+ servers available)
- Token cost optimization (15x multiplier mitigation)
- Layered memory architecture (working → episodic → semantic)
- Competitive positioning against 19 analyzed platforms
- Freemium pricing structure with reverse trial
- Agent Pack marketplace architecture
- Observability and audit trail requirements

---

## 1. MARKET POSITION

### The Gap No One Fills

19 competitors analyzed. None combine:
1. True shared-environment multi-agent collaboration
2. Pre-built domain-specific agent packs
3. Model-agnostic LLM routing
4. SaaS accessibility without engineering requirements
5. Domain knowledge bases with verified legal/construction data

CrewAI and LangGraph require engineers. Cloud providers (Bedrock, Vertex) lock you into ecosystems. Commercial SaaS (Dust.tt) doesn't support custom multi-agent orchestration. Ciphergy occupies white space.

### Market Size

| Segment | 2025 | 2030 | CAGR |
|---------|------|------|------|
| AI Agent Platform (total) | $7.5B | $47-53B | 44% |
| Multi-Agent Systems | $4.0B | $28B | 48.5% |
| Vertical AI Agents | Fastest segment | — | 62.7% |
| Legal AI | $2.1-2.8B | $15B+ | 30%+ |
| Construction AI | $3.9-5.1B | $13B+ | 17-25% |

### Why Vertical-First Wins

Gartner: 40% of enterprise apps will incorporate AI agents by end of 2026. But 40%+ of agentic AI projects will be scrapped by 2027 due to unclear value. The platforms that survive deliver **measurable domain-specific ROI**, not horizontal "build your own agent" toolkits.

Lead with Legal Litigation Pack. Expand to Construction. Then open the platform for custom agent packs.

---

## 2. TECHNICAL ARCHITECTURE

### Stack (Confirmed)

| Layer | Technology | Host |
|-------|-----------|------|
| Frontend | React/Vite or Expo React Native | Cloudflare Pages |
| Backend API | Python (FastAPI) | AWS ECS Fargate |
| Database | Neon (Serverless Postgres) → AWS Aurora | AWS |
| Vector Store | pgvector (in Postgres) | Same DB |
| Queue | ARQ (async Redis queue) | AWS ElastiCache |
| Secrets | AWS Secrets Manager | AWS |
| CI/CD | GitHub Actions | GitHub |
| CDN/WAF | Cloudflare | Cloudflare |
| LLM Primary | Anthropic API (Claude) | Anthropic |
| LLM Fallback | OpenAI, Google Vertex | Multi-provider |
| LLM Router | LiteLLM (library, not proxy) | In-process |
| Integration Protocol | MCP (Model Context Protocol) | Self-hosted servers |

### Backend Architecture

**Three-tier task processing:**
1. **Synchronous** — `asyncio` for concurrent agent sessions, `asyncio.gather()` for parallel LLM calls
2. **Lightweight async** — FastAPI `BackgroundTasks` for logging, telemetry, webhook delivery
3. **Heavy async** — ARQ (Redis queue) for long-running agent workflows, document generation, batch operations

**Why ARQ over Celery:** ARQ's native async model integrates cleanly with FastAPI's event loop. Celery's synchronous workers create conflicts with async code.

**Transport:** SSE (Server-Sent Events) as default. Multiplexed by `agent_id`:
```json
{"agent_id": "red_team", "type": "token", "content": "The", "seq": 42}
```
WebSocket only for bidirectional needs: user interrupts, interactive tool approval, multi-user collaboration.

### Database Schema (Core Tables)

```
tenants          — Multi-tenant isolation (RLS enforced)
users            — Auth, roles, permissions
projects         — Shared context per engagement/case
agents           — Definitions: system prompts, tool configs, weights
conversations    — Threads within projects
messages         — Individual turns with token usage + cost tracking
tool_calls       — Audit log of every external action
knowledge_entries — Domain knowledge with vector embeddings (pgvector)
checkpoints      — Agent state snapshots for rollback/replay
agent_runs       — Execution logs: input, output, cost, duration, verdict
```

**Multi-tenancy:** Postgres Row-Level Security from day one. `tenant_id` on every table. `SET LOCAL` at transaction start. JWT tokens with tenant-scoped claims.

### Cost Management (CRITICAL)

Multi-agent systems use **~15x more tokens** than single chats. Without controls, a single uncontrolled agent loop can generate thousands of dollars in API costs.

**Four layers of protection:**
1. **Redis rate limiter** — per-user and per-tenant RPM on API endpoints
2. **Token budget tracking** — pre-request estimation + post-request recording from API responses
3. **USD cost budget** — per-tenant monthly caps with soft (warning) and hard (block) thresholds
4. **Agent loop protection** — 25 max iterations per run, per-run token budget, execution timeouts, circuit breakers on consecutive errors

**Three cost optimization strategies:**
1. **Prompt caching** — Anthropic's cache reduces costs 90% on cached reads. Cache every agent's system prompt + tool definitions.
2. **Model tiering via LiteLLM** — Simple tasks → Haiku ($1/M input). Standard → Sonnet ($3/M). Complex reasoning → Opus ($15/M).
3. **Independent scratchpads** — Each agent maintains private working context. Only final outputs enter shared state. Reduces token usage ~67% vs full-transparency approaches.

---

## 3. AGENT ARCHITECTURE

### Legal Litigation Pack — 5 Agents (from Claude Code Roadmap)

| Agent | Weight | Role | Veto Power |
|-------|--------|------|-----------|
| **Lead Counsel** | 30% | Strategy, case command, user interface, final approval | No |
| **Research & Citation Counsel** | 25% | Legal research, citation verification, anti-hallucination loop | No |
| **Drafting Counsel** | 15% | All written output, court formatting, .docx/.pdf generation | No |
| **Adversarial Counsel (Red Team)** | 20% | Opposing counsel simulation, stress testing, risk scoring | No |
| **Compliance & Procedure Counsel** | 10% + VETO | Deadlines, jurisdictional rules, procedural compliance | **YES — absolute veto on procedural errors** |

### Orchestration Pattern: Supervisor with Concurrent Fan-Out

**Validated by research:** Google DeepMind (Dec 2025) found unstructured multi-agent networks amplify errors up to 17.2x. The supervisor pattern is recommended by Microsoft Azure Architecture Center, LangChain, and production practitioners.

**How it works in Ciphergy:**

```
User Input
    │
    ▼
LEAD COUNSEL (Supervisor)
    │
    ├── Classifies task type
    ├── Routes to appropriate agent(s)
    ├── Can invoke single agent or fan-out to multiple
    │
    ▼ [Fan-out for substantive work]
┌─────────────┬──────────────┬──────────────┐
│  RESEARCH   │  DRAFTING    │  RED TEAM    │
│  Counsel    │  Counsel     │  Counsel     │
│  (parallel) │  (sequential │  (parallel   │
│             │  after       │  with draft) │
│             │  research)   │              │
└──────┬──────┴──────┬───────┴──────┬───────┘
       │             │              │
       └─────────────┼──────────────┘
                     │
                     ▼
           COMPLIANCE COUNSEL
           (Final gate — can VETO)
                     │
                     ▼
              LEAD COUNSEL
              (Aggregates, scores, presents)
                     │
                     ▼
              USER (Approve / Revise)
```

### Weighted Debate Consensus (WDC v2.0)

Every substantive output runs through all 5 agents. Each scores the output:

| Score Range | Verdict | Action |
|------------|---------|--------|
| 8.5+ | CERTIFIED | Output approved, deliver to user |
| 7.0-8.4 | CERTIFIED WITH NOTES | Approved with flagged concerns |
| 5.0-6.9 | REVISION REQUIRED | Sent back to Drafting with specific feedback |
| <5.0 | REJECTED | Fundamental issue — requires strategy reassessment |

**Compliance Agent override:** Regardless of aggregate score, Compliance can VETO any output with a procedural defect. A missed deadline, wrong court format, or incorrect filing fee = automatic rejection regardless of how well the legal substance scores.

### Agent Communication: Shared Blackboard + Private Scratchpads

- **Shared state (blackboard):** All agents read from and write to a centralized project state object. Contains: case facts, evidence inventory, claim matrix, timeline, open questions, confidence scores.
- **Private scratchpads:** Each agent maintains working context invisible to others. Only final outputs and structured conclusions enter the shared state.
- **Why:** Controls token costs (67% reduction) and prevents agents from being influenced by each other's intermediate reasoning, which research shows degrades output quality.

### Memory Architecture (Three Layers)

| Layer | Storage | Access Speed | Purpose |
|-------|---------|-------------|---------|
| Working Memory | Redis | Sub-millisecond | Current task state, active conversation |
| Episodic Memory | Postgres + pgvector | Low millisecond | Conversation history, agent runs, case events |
| Semantic Memory | pgvector embeddings | Medium millisecond | Cross-session knowledge retrieval, case law, precedent |

**Checkpointing:** LangGraph-style state snapshots at every transition. Enables: time-travel debugging, rollback to last-known-good, what-if analysis from forked checkpoints, and complete audit trails.

---

## 4. THE 12 WINNING-EDGE ENHANCEMENTS (from Claude Code)

These transform Ciphergy from a document preparation tool into a **litigation execution engine**. Each enhancement is a link in the chain: research → draft → file → force production → use in RFAs → unanswered RFAs → summary judgment → settlement.

### E1: Evidence Weaponization Engine
- Element-evidence matrix mapping every claim element to specific evidence
- Discovery sequencing: what to request, in what order, to build toward what admission
- Impeachment preparation: contradictions between testimony, documents, and public statements
- **Agent owner:** Research Counsel + Red Team (collaborative)

### E2: Settlement Pressure Engine
- Models opposing party's litigation cost trajectory month-by-month
- Identifies pressure points: insurance policy limits, personal asset exposure, reputational risk
- Generates strategic demand letters calibrated to opposing party's pain threshold
- Calculates the "rational settlement zone" where both parties' expected values intersect
- **Agent owner:** Lead Counsel + Research Counsel

### E3: Motion Practice Warfare
- Offensive motion sequencing: what to file, when, to strip away which defense
- RFA warfare: craft admissions that, if unanswered, become deemed admitted → partial SJ
- Summary judgment attack packages assembled from discovery production
- Progressive defense elimination through sequential motions
- **Agent owner:** Lead Counsel (strategy) + Drafting Counsel (production) + Red Team (stress test)

### E4: Judicial Analytics
- Judge profiles from CourtListener ruling data
- Ruling pattern analysis: what arguments this judge favors, what they reject
- Adaptive brief writing: mirror the judge's own reasoning patterns
- Hearing preparation tailored to judge's questioning style
- **Agent owner:** Research Counsel
- **Data source:** CourtListener API (free), RECAP archive

### E5: Damages Maximization
- Full taxonomy of available damages by claim type and jurisdiction
- Claim stacking identification: same facts → multiple theories → multiplied recovery
- Interest calculations (pre-judgment, post-judgment, statutory)
- Fee-shifting statute identification (prevailing party attorney's fees)
- **Agent owner:** Research Counsel + Lead Counsel

### E6: Opposing Party Scanner
- Public records deep scan: prior litigation, liens, judgments, bankruptcies, corporate filings
- Pattern litigation detection: have they been sued for the same conduct before?
- Financial viability assessment: can they pay a judgment?
- Insurance coverage probability analysis
- **Agent owner:** Research Counsel
- **Data sources:** PACER, CourtListener, county records, SOS/Sunbiz, SEC EDGAR

### E7: Procedural Trap Detector
- Monitors opposing party's compliance with deadlines, court orders, discovery obligations
- Auto-detects: late filings, missed RFA responses (= deemed admitted), discovery violations
- Generates motion to compel templates when violations are detected
- Tracks sanctions eligibility for repeated violations
- **Agent owner:** Compliance Counsel (monitoring) + Drafting Counsel (motion generation)

### E8: Case Narrative Engine
- Theory of the case development with coherent narrative arc
- Visual timeline generation for judge/jury consumption
- Jury instruction alignment: draft arguments that map directly to jury instructions
- Theme development and testing
- **Agent owner:** Lead Counsel + Red Team (tests narrative against opposing narrative)

### E9: Real-Time Case Law Monitoring
- CourtListener webhook alerts for new opinions citing relevant statutes
- Legislative change tracking for statutes in play
- New favorable opinion → auto-suggested supplemental authority filing
- **Agent owner:** Research Counsel
- **Integration:** CourtListener MCP server (to be built)

### E10: Pro Se Credibility Optimizer
- Professional formatting engine (Pennington Standard as template)
- First-filing shock value: when the complaint looks indistinguishable from a top firm's work
- Correspondence standards: every outgoing communication in glacier mode
- Filing quality score: pre-submission review against jurisdiction-specific format requirements
- **Agent owner:** Drafting Counsel + Compliance Counsel

### E11: Compliance Monitoring Dashboard
- Court order obligation tracker: what the court ordered, by when, compliance status
- Opposing party compliance tracker: their deadlines, their obligations, their failures
- Auto-generates motion to compel when opposing party violates a deadline
- Calendar integration with tiered reminders (14/7/3/1 day)
- **Agent owner:** Compliance Counsel

### E12: Appeal Preservation Engine
- Issue preservation tracker: every legal issue raised, objected to, and ruled upon
- Objection generator: real-time prompting to make objections that preserve appellate issues
- Post-trial motion automation: JNOV, new trial, remittitur templates
- Appellate timeline computation with jurisdiction-specific rules
- **Agent owner:** Compliance Counsel + Research Counsel

---

## 5. INTEGRATION ARCHITECTURE — MCP-FIRST

### Why MCP

Anthropic donated MCP to the Linux Foundation (Dec 2025). OpenAI, Google DeepMind, Block, and AWS adopted it. 1,200+ MCP servers cataloged. It is the "USB-C for AI" — the universal connector standard.

**Every Ciphergy integration should be an MCP server.** This makes:
- Every integration portable across LLM providers
- The platform extensible by the entire open-source ecosystem
- Domain-specific servers (legal research, OSHA compliance, construction permits) contribute back as community assets

### Priority MCP Servers to Build/Integrate

**Legal Domain:**
| Server | Source | Cost | Data |
|--------|--------|------|------|
| CourtListener | Free Law Project | Free | Case law, RECAP, judge data |
| PACER Case Locator | US Courts | $0.10/page | Federal court filings |
| US Code / eCFR | govinfo.gov | Free | Federal statutes, regulations |
| State Statutes | Various | Free | State-specific law |
| Google Scholar Legal | Google | Free | Case law search |
| SEC EDGAR | SEC | Free | Corporate filings |
| Westlaw API | Thomson Reuters | Paid | Premium case law, KeyCite |

**Construction Domain:**
| Server | Source | Cost | Data |
|--------|--------|------|------|
| Procore API | Procore | Paid | Projects, RFIs, budgets, safety |
| OSHA Data | DOL | Free | Inspections, violations since 1973 |
| Autodesk Construction Cloud | Autodesk | Paid | Plans, BIM, submittals |
| PermitFlow | PermitFlow | Paid | Building permits |
| County Property Records | Various | Free/Low | Ownership, liens, valuations |

**Cross-Domain:**
| Server | Source | Data |
|--------|--------|------|
| Google Drive | Google Workspace | Document storage/search |
| Google Calendar | Google Workspace | Deadline management |
| Gmail | Google Workspace | Correspondence |
| Slack | Salesforce | Team communication |
| Asana/Jira/Linear | Various | Project management |
| DocuSign | DocuSign | E-signatures |
| Stripe | Stripe | Payment tracking |

### Document Generation (Not MCP — Internal)

| Library | Use | Output |
|---------|-----|--------|
| docxtpl | DOCX from Jinja2 templates | Court filings, motions, briefs |
| WeasyPrint | HTML → PDF | Research memos, reports |
| Both use Jinja2 | Unified templating | Consistent variable injection |

---

## 6. VERIFIED LEGAL KNOWLEDGE BASE

### Free/Low-Cost Legal Data APIs (13+ identified by Claude Code)

1. **CourtListener / RECAP** — 12M+ court opinions, judge profiles, PACER data
2. **US Code (govinfo.gov)** — Complete federal statutory law
3. **eCFR (ecfr.gov)** — Electronic Code of Federal Regulations
4. **Google Scholar Legal** — Case law search
5. **PACER Case Locator** — Federal court case search ($0.10/page)
6. **SEC EDGAR** — Corporate filings, financial disclosures
7. **State Secretary of State APIs** — Entity searches (Sunbiz, etc.)
8. **CFPB Complaint Database** — Consumer financial complaints
9. **OSHA Data Portal** — Safety violations, inspections
10. **Census/Demographic Data** — Jury pool analysis
11. **Federal Register** — Proposed/final regulations
12. **State Legislature APIs** — Bill tracking, statute updates
13. **FOIA.gov** — Freedom of information request tracking

### Anti-Hallucination Loop (Research Counsel)

Every citation goes through a 5-step verification:
1. Does this case/statute actually exist? (Search to verify)
2. Is the citation format correct for the jurisdiction?
3. Does the case actually hold what's being attributed? (If unverifiable → flag)
4. Is the case still good law? (Note: full KeyCite/Shepard's requires paid access — instruct user)
5. Is the statute the current version? (Search for amendments)

**Confidence flagging on every assertion:**
- High: Well-established, recently verified — no flag
- Moderate: May be outdated or jurisdiction-dependent — "[Verify in your jurisdiction]"
- Low: General knowledge without specific verification — "[UNVERIFIED — research before relying]"

---

## 7. AGENT PACK MARKETPLACE

### Architecture

Each pack is a YAML manifest defining:
```yaml
pack:
  name: "Legal Litigation Pack"
  version: "1.0"
  domain: "legal"
  agents:
    - id: lead_counsel
      name: "Lead Counsel"
      weight: 0.30
      system_prompt_ref: "prompts/lead_counsel.md"
      tools: [case_search, statute_lookup, calendar_create]
      model_tier: "reasoning"  # routes to Opus
    - id: research_counsel
      # ...
  workflows:
    - id: case_intake
      steps: [extract_facts, research_claims, assess_viability]
      agents: [research_counsel, lead_counsel]
    - id: draft_complaint
      steps: [research, outline, draft, red_team, compliance_check, finalize]
      agents: [research_counsel, drafting_counsel, red_team, compliance_counsel, lead_counsel]
  templates:
    - id: complaint_template
      format: docx
      file: "templates/complaint.docx"
  knowledge_bases:
    - id: florida_statutes
      source: "flsenate.gov"
      refresh: "weekly"
```

### Customization Levels

| Level | Who | What They Can Do |
|-------|-----|-----------------|
| No-code | Any user | Toggle agents on/off, change names, modify templates via visual editor |
| Low-code | Power user | Add/remove tasks, modify workflow sequences, connect new integrations via config |
| Full-code | Developer | Create custom tools, modify agent logic, build new agents via API/SDK |

### V1 Packs

1. **Legal Litigation Pack** — 5 agents, 12 winning-edge enhancements, 13+ data sources, court-ready document generation
2. **Construction Management Pack** — 6 agents (Scheduler, Compliance, Estimator, Safety, Document, Subcontractor), Procore/OSHA/permit integration
3. **Business Operations Pack** — 5 agents (Analyst, Financial, Strategy, Operations, Communications)

---

## 8. PRO SE FEATURES (Phase 6 from Claude Code Roadmap)

These features specifically serve self-represented litigants — Ciphergy's origin story and a massively underserved market:

1. **Plain Language Translator** — Converts legal jargon to plain English and vice versa
2. **Fee Waiver Assistant** — Identifies eligibility, generates IFP petitions
3. **Judge Profile Cards** — CourtListener-sourced ruling patterns, preferences, tendencies
4. **Court Form Finder** — Locates jurisdiction-specific forms with pre-fill
5. **Legal Aid Screener** — Identifies free/low-cost legal resources if case exceeds self-representation capacity
6. **Deadline Calculator** — Jurisdiction-aware computation with holiday exclusions
7. **Service of Process Guide** — Step-by-step for each jurisdiction and service method

---

## 9. OBSERVABILITY & AUDIT

### Why This Matters

Only 11% of AI agent pilots reach production. 60% of organizations don't fully trust AI agents. The pilot-to-production gap is the market's defining problem. Observability is how Ciphergy crosses it.

### What Gets Tracked

| Category | Data | Storage |
|----------|------|---------|
| Agent Runs | Input, output, model used, tokens, cost, duration, verdict | Postgres |
| Tool Calls | Tool name, input, output, success/failure, latency | Postgres |
| WDC Debates | Each agent's score, reasoning, final aggregate | Postgres |
| Compliance Vetoes | What was vetoed, why, what changed | Postgres |
| User Approvals | What was presented, what was approved/rejected, latency | Postgres |
| Cost | Per-run, per-agent, per-tenant, per-model, daily/monthly rollups | Postgres + Redis cache |
| Errors | Agent failures, API errors, timeout events | Postgres + alerting |

### User-Facing Dashboard

- **Cost tracker** — Real-time spend vs budget, projected month-end
- **Agent activity feed** — What each agent did, when, why
- **Confidence scores** — Per-claim evidence confidence (legal domain)
- **Deadline tracker** — Visual calendar with color-coded urgency
- **Audit trail** — Exportable log of every agent action for compliance/discovery

---

## 10. PRICING

### Freemium with Reverse Trial

**14-day reverse trial:** New users get Pro features for 2 weeks, then downgrade to Free. Converts 2-3x better than standard freemium.

| Feature | Free ($0) | Pro ($29/mo) | Team ($49/user/mo) | Enterprise (Custom) |
|---------|-----------|-------------|-------------------|-------------------|
| Agents per workflow | 2 | 10 | 25 | Unlimited |
| Agent runs/month | 50 | Unlimited (budget models) | Unlimited | Unlimited |
| Premium model credits | None | $25/mo pool | $40/user/mo pool | Custom |
| Projects | 3 (public) | 10 (private) | Unlimited | Unlimited |
| Agent Packs | Basic only | All packs | All packs + custom | Custom packs |
| Custom agents | No | Yes | Yes | Yes |
| API access | No | Yes | Yes | Yes |
| Team collaboration | No | No | Yes (RBAC) | Yes (SAML SSO) |
| Log retention | 24 hours | 7 days | 30 days | Custom |
| Support | Community | Email | Priority | Dedicated + SLA |
| MCP connectors | 3 | 10 | Unlimited | Unlimited |

**Credit transparency:** "1 credit ≈ 1 simple agent run. 5 credits ≈ 1 complex multi-agent workflow." Show clear conversions. Never surprise users with costs.

**Target metrics:** 5-8% free-to-paid conversion. First successful multi-agent run within 5 minutes of signup.

---

## 11. BUILD ROADMAP (Revised from Claude Code's 8 Phases)

### Phase 0: Foundation (Weeks 1-2)
- FastAPI skeleton with auth, multi-tenancy, RLS
- Neon Postgres schema (core tables above)
- Cloudflare Pages frontend scaffold (React/Vite)
- GitHub Actions CI/CD pipelines (wrangler.toml + task-def.json)
- LiteLLM integration with model tiering
- Redis/ARQ setup for async task processing

### Phase 1: Agent Core (Weeks 3-5)
- Agent definition system (YAML manifests → runtime)
- Supervisor orchestration with fan-out/fan-in
- Shared blackboard + private scratchpad state management
- WDC v2.0 scoring system
- Compliance veto gate
- SSE streaming for real-time agent output
- Basic conversation UI

### Phase 2: Legal Knowledge Base (Weeks 6-8)
- CourtListener MCP server (case law, judge profiles)
- US Code / eCFR MCP server (federal statutes)
- Google Scholar legal search integration
- pgvector embeddings for semantic legal search
- Anti-hallucination citation verification loop
- State statute lookup (Florida first, then expand)

### Phase 3: Case Management Engine (Weeks 9-11)
- Project/case state machine (intake → research → strategy → drafting → filing → discovery → trial)
- Evidence inventory with element-evidence matrix (E1)
- Claim confidence scoring system
- Deadline computation with jurisdiction-specific rules
- Calendar integration (Google Calendar MCP)
- Settlement pressure modeling (E2)

### Phase 4: Document Generation (Weeks 12-14)
- docxtpl template engine for court filings
- WeasyPrint for PDF generation
- Pennington Standard as default legal template
- Template library: complaints, motions, briefs, demand letters, discovery
- Filing format validation per jurisdiction
- Pro Se Credibility Optimizer (E10)

### Phase 5: Integrations (Weeks 15-17)
- Google Drive MCP (document storage/search)
- Gmail MCP (correspondence)
- Slack MCP (team updates)
- Asana MCP (project management)
- PACER Case Locator integration
- Opposing Party Scanner (E6) — public records APIs

### Phase 6: Winning Edge Features (Weeks 18-21)
- Motion Practice Warfare engine (E3)
- Judicial Analytics (E4)
- Damages Maximization (E5)
- Procedural Trap Detector (E7)
- Case Narrative Engine (E8)
- Real-Time Case Law Monitoring (E9)
- Compliance Monitoring Dashboard (E11)
- Appeal Preservation Engine (E12)

### Phase 7: Pro Se & Marketplace (Weeks 22-24)
- Plain language translator
- Fee waiver assistant
- Judge profile cards
- Court form finder
- Legal aid screener
- Agent Pack marketplace (install, customize, publish)
- Construction Management Pack
- Business Operations Pack

### Phase 8: Hardening & Launch (Weeks 25-28)
- Load testing and cost optimization
- Security audit
- SOC 2 preparation
- Observability dashboard
- Pricing/billing system (Stripe integration)
- Onboarding flow with 5-minute time-to-value
- 14-day reverse trial implementation
- Documentation and API reference
- Beta launch on ciphergy.ai

---

## 12. COMPETITIVE MOAT

### What Ciphergy Has That No One Else Does

1. **Battle-tested architecture.** The DualAI prototype ran a real civil litigation case (Pennington v. Campenni) through the full lifecycle — from pre-suit demand through e-filing through Phase 2 preparation. Every design decision was validated against actual procedural pressure, not hypothetical scenarios.

2. **Domain-specific winning-edge features.** The 12 enhancements (E1-E12) go beyond "AI can draft documents" to "AI can execute litigation strategy." No competitor offers settlement pressure modeling, motion practice sequencing, or procedural trap detection.

3. **Compliance veto power.** The Compliance agent's absolute veto on procedural errors is architecturally unique. In legal work, a missed deadline is worse than a bad argument — it's malpractice. Building this as a hard gate, not a suggestion, reflects real-world stakes.

4. **Pro se market ownership.** 72% of civil cases in many jurisdictions involve at least one self-represented party. Harvey AI targets BigLaw at $8B valuation. Ciphergy targets the 72% that Harvey ignores — at a price point ($29/month) that makes professional-quality legal work accessible.

5. **MCP-first extensibility.** Every integration is an MCP server, making Ciphergy a platform that the open-source community extends, not a walled garden that the company must maintain alone.

6. **The Extraction Prompt as onramp.** The Total Case Extraction Prompt (22 sections) means users can migrate from ANY prior AI session — GPT, Gemini, Cursor, Claude — into Ciphergy with zero data loss. No competitor has a structured migration tool.

---

## 13. V2 → V3 ENHANCEMENT CANDIDATES

For future versions, based on research findings:

1. **Multi-user collaboration** — Multiple team members working on the same case with role-based agent access
2. **Voice interface** — Dictate facts, receive analysis, approve outputs by voice
3. **Mobile-first case management** — Expo React Native for courthouse use
4. **AI deposition assistant** — Real-time suggested questions during depositions
5. **Automated court filing** — Direct e-filing integration (PACER/ECF, state portals)
6. **Opposing counsel profiling** — DBPR/bar records + litigation history = behavioral prediction
7. **Multi-jurisdiction support** — Automatic adaptation of templates, deadlines, and procedures when jurisdiction changes
8. **Client portal** — Case status dashboard for clients (attorneys using Ciphergy for their practice)
9. **Billable time tracking** — For attorneys, track time spent on AI-assisted vs manual work
10. **Regulatory compliance monitoring** — Beyond legal: OSHA, EPA, DBPR, building code changes

---

**CONFIDENTIAL — Bo Pennington / Pentek Design Build LLC**
**No portion of this document may be shared without express written authorization.**

*Ciphergy V2.0 — March 15, 2026*
*Cipher + Energy: Turns noise into signal. Turns signal into action.*
