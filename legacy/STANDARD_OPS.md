# STANDARD OPERATING PROCEDURES
## Ciphergy — System Architecture & Automation Reference
## V1.0 | March 8, 2026

---

# SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE SESSION                       │
│                                                             │
│  SessionStart ──→ session-startup.sh                        │
│       │            ├── nerve_center.py startup               │
│       │            │   ├── Milestone check (alert < 7 days)  │
│       │            │   ├── Intake folder check               │
│       │            │   └── Dashboard render                  │
│       │            └── agent_comm.py read (if configured)    │
│       ▼                                                      │
│  User Request ──→ Claude processes                           │
│       │                                                      │
│       ▼                                                      │
│  Edit/Write ──→ PostToolUse hooks fire automatically:       │
│       │                                                      │
│       ├── post-edit-logger.sh    → DIFF/ auto-log            │
│       └── auto-docx.sh          → Word doc to User/ folder   │
│                                                              │
│  PreToolUse ──→ Data classification guard                    │
│       └── Blocks sensitive data from leaving the machine     │
└─────────────────────────────────────────────────────────────┘
```

---

# LAYER MODEL

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Hook Entry** | Bash (.sh) | Claude Code fires these on lifecycle events |
| **Logic Engine** | Python (.py) | Cascade engine, comm bus, scoring, document generation |
| **Hook Config** | JSON (.claude/settings.json) | Tells Claude Code WHEN to fire hooks |
| **Protocol** | YAML (.yaml) | Tells Claude HOW to communicate, classify data, configure domain |
| **Output** | Markdown (.md) | Templates and context files (fast for Claude to read) |
| **Delivery** | Word (.docx) | Professional formatted docs for human consumption |
| **Security** | Python (crypto.py) + YAML (data_classification.yaml) | AES-256-GCM encryption + transmission guards |

---

# HOOK REGISTRY

| # | Hook | Event | What It Does |
|---|------|-------|-------------|
| 1 | **Session Startup** | SessionStart | Runs nerve_center.py (milestones, intake, dashboard) + agent comms |
| 2 | **Diff Logger** | PostToolUse (Edit/Write) | Logs every file change to DIFF/ |
| 3 | **Auto DOCX** | PostToolUse (Edit/Write) | Converts reportable .md to Word docs in User/ folder |
| 4 | **Data Guard** | PreToolUse (Bash) | Blocks sensitive data from leaving the machine |

---

# SCRIPT REGISTRY

| # | Script | Purpose | Commands |
|---|--------|---------|----------|
| 1 | `nerve_center.py` | Cascade engine | `startup`, `deadlines`, `dashboard`, `intake`, `diff` |
| 2 | `agent_comm.py` | Inter-agent bus (Agent Local ↔ Agent Cloud) | `read`, `write`, `status` |
| 3 | `crypto.py` | AES-256-GCM encryption | `keygen`, `encrypt`, `decrypt`, `test` |
| 4 | `sanitize_sync.py` | 6-tier content sanitization | `check`, `sanitize`, `audit` |

---

# CONFIG FILES

| # | File | Format | Purpose |
|---|------|--------|---------|
| 1 | `.claude/settings.json` | JSON | Hook configuration |
| 2 | `config/ciphergy.yaml` | YAML | Master config — domain, agents, bus, thresholds |
| 3 | `config/data_classification.yaml` | YAML | What can/cannot leave the machine |
| 4 | `config/domain_profiles/*.yaml` | YAML | Domain vocabulary mappings (legal, medical, investigation, engineering) |
| 5 | `config/jurisdictions/*.yaml` | YAML | Jurisdiction-specific statutes, courts, regulatory bodies |

---

# AGENT MESH — 5 AI Agents

| # | Agent | Role | Trigger |
|---|-------|------|---------|
| 1 | **Onboarding** | Guides user from zero to operational | First session / "set up" |
| 2 | **Evidence Coach** | Scores data, identifies gaps | New data uploaded |
| 3 | **Deadline Sentinel** | Always watching milestones | Every session startup |
| 4 | **Draft Guardian** | 7-gate filter on outbound comms | Any outbound draft |
| 5 | **Strategy Advisor** | Three Moves Ahead on decisions | Decision points |

---

# TEMPLATE REGISTRY

| # | Template | Trigger |
|---|----------|---------|
| 1 | `ENTITY_ANALYSIS.template.md` | "analyze [entity]" |
| 2 | `OUTPUT_DRAFT.template.md` | Any outbound communication |
| 3 | `SOURCE_PREP.template.md` | "prep [source]", "declaration" |
| 4 | `EVIDENCE_INTAKE.template.md` | New data received |
| 5 | `DELIVERABLE_CHECKLIST.template.md` | Before any submission |
| 6 | `ADVERSARY_PLAYBOOK.template.md` | When adversary makes a move |
| 7 | `SITUATION_DASHBOARD.template.md` | Every session startup |
| 8 | `MILESTONE_TRACKER.template.md` | Every session startup |
| 9 | `CROSS_PROJECT_SYNC.template.md` | Cross-project intelligence |

---

# CASCADE RULES

| Trigger | Updates |
|---------|---------|
| New data uploaded | Confidence Monitor → Entity Analyses → Alerts → Dashboard → DIFF |
| Confidence score changed | Entity Analyses → Dashboard → Deliverable version flag → DIFF |
| Entity Analysis updated | Dashboard → DIFF → auto-docx |
| Milestone approaching | Alerts → Dashboard → User notification |
| Template/script improved | sanitize_sync → DIFF |

---

# DATA CLASSIFICATION

| 🔴 LOCAL ONLY | 🟡 SIGNAL OK | 🟠 ENCRYPTED | 🟢 PUBLIC |
|---|---|---|---|
| Entity data, strategy, scores | Status, file paths, timestamps | Content that MUST transit | Sanitized product code |
| NEVER leaves machine | External bus only | AES-256-GCM required | Any channel |

---

# FOLDER STRUCTURE

```
CIPHERGY/
├── .claude/hooks/          ← Automated hooks
├── .keys/                  ← Encryption keys (gitignored)
├── agents/                 ← 5 AI agent definitions
├── config/
│   ├── ciphergy.yaml       ← Master config
│   ├── data_classification.yaml
│   ├── domain_profiles/    ← Domain vocabulary plugins
│   └── jurisdictions/      ← Jurisdiction modules
├── ciphergy/               ← Python package (core logic)
├── core/                   ← Protocol files (gates, panel, guardrails)
├── scripts/                ← Python engines
├── templates/              ← 9 output format templates
├── tests/                  ← Test suite (8 tests, all passing)
├── docs/                   ← Documentation
├── New-Data/               ← Intake folder
├── DIFF/                   ← Audit trail
└── STANDARD_OPS.md         ← This file
```

---

*STANDARD_OPS.md V1.0 — Ciphergy*
*Domain-agnostic. Cross-domain. Signal from noise.*
