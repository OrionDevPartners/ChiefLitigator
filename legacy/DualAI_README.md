# DualAI — Dual-Environment AI Orchestration System

## A framework for running two AI instances in parallel with persistent state, automated sync, and asynchronous communication via a shared project management layer.

**Version:** 1.0
**Created:** March 7, 2026
**Author:** Bo Pennington + Claude (Anthropic)
**First deployment:** Pennington v. Campenni civil litigation

---

## Table of Contents

1. [What Is DualAI](#1-what-is-dualai)
2. [The Problem It Solves](#2-the-problem-it-solves)
3. [Architecture Overview](#3-architecture-overview)
4. [The Two Environments](#4-the-two-environments)
5. [The Bridge Layer — Asana](#5-the-bridge-layer--asana)
6. [Version Control System](#6-version-control-system)
7. [Sync Agent & Project Knowledge Pipeline](#7-sync-agent--project-knowledge-pipeline)
8. [The User's Role — Human as Router](#8-the-users-role--human-as-router)
9. [Complete File Inventory](#9-complete-file-inventory)
10. [System Requirements](#10-system-requirements)
11. [Setup Guide](#11-setup-guide)
12. [How It Works — Step by Step](#12-how-it-works--step-by-step)
13. [CLI Reference](#13-cli-reference)
14. [Use Cases Beyond Law](#14-use-cases-beyond-law)
15. [Limitations & Known Constraints](#15-limitations--known-constraints)
16. [Design Philosophy](#16-design-philosophy)

---

## 1. What Is DualAI

DualAI is an orchestration pattern for running two Claude AI instances as specialized parallel workers on the same project, connected through a shared project management tool (Asana) and a version-controlled file sync system. Neither instance can see the other. They communicate asynchronously through structured messages posted to Asana task comments, and stay synchronized through a monitored file system that detects changes and alerts the human operator when files need to be transferred between environments.

The human operator sits at the center — not as a bottleneck, but as a router. The system is designed so that the human's role is reduced to three physical actions: dragging files, pasting output, and confirming decisions. All intelligence about *what* needs to move, *when*, and *why* lives inside the system itself.

---

## 2. The Problem It Solves

### The Core Constraint

Claude Code (terminal-based) and Claude.ai (web-based) are different products with different capabilities. They cannot share memory, context, files, or conversation history. A conversation in one environment is invisible to the other. There is no API bridge, no shared filesystem, no pub/sub channel.

But each environment has capabilities the other lacks:

| Capability | Claude Code | Claude.ai Desktop |
|-----------|------------|-------------------|
| Local filesystem read/write | Yes (full repo access) | No |
| File count capacity | 663+ files, 1M+ context | ~35 project knowledge files |
| Parallel agents | Up to 20 concurrent | Single thread |
| Internet access | Yes | Yes (web search) |
| Persistent memory across sessions | Via files in repo | Via system memory (7 slots) + project knowledge |
| Document creation (docx, pdf, xlsx) | Limited | Full skill library |
| MCP integrations | Asana, others | Asana, Gmail, Slack, others |
| Strategic conversation | Limited (task-focused) | Optimized (conversational, contextual) |
| Past conversation search | No | Yes |

Running complex projects means you need both. The question is: how do you keep them synchronized without the human becoming a full-time context shuttle?

### What Existing Solutions Miss

Manual copy-paste works for simple handoffs but fails at scale. When one environment updates 4 files during a cascade, the human doesn't know which files changed, whether the changes affect the other environment, or whether the versions are still aligned. Without a system, state drift is inevitable — and in a domain like litigation, state drift means filing the wrong version of a court document.

DualAI solves this by making the sync process deterministic: every change is detected, every affected file is flagged, every stale file is surfaced to the human with an exact list of what to upload and where.

---

## 3. Architecture Overview

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│       CLAUDE CODE           │     │      CLAUDE.AI DESKTOP      │
│   (Opus 4.6, terminal)      │     │   ("Legal Pro" project)     │
│                             │     │                             │
│ ┌─────────────────────────┐ │     │ ┌─────────────────────────┐ │
│ │ Local Repo (713 files)  │ │     │ │ Project Knowledge (35)  │ │
│ │ VERSION_REGISTRY.json   │ │     │ │ System Memory (8 slots) │ │
│ │ VERSION_RULES.yaml      │ │     │ │ Past Chat Search        │ │
│ │ auto_version.sh         │ │     │ │ File Creation Skills    │ │
│ │ Evidence Monitoring     │ │     │ │ Web Search              │ │
│ │ 20 Parallel Agents      │ │     │ │ Strategic Analysis      │ │
│ └─────────────────────────┘ │     │ └─────────────────────────┘ │
│                             │     │                             │
│     WRITES ──────┐          │     │          ┌────── WRITES     │
│     READS ───┐   │          │     │          │   ┌── READS      │
└──────────────┼───┼──────────┘     └──────────┼───┼──────────────┘
               │   │                           │   │
               │   ▼                           ▼   │
          ┌────┼────────────────────────────────────┼───┐
          │    │         ASANA (shared)              │   │
          │    │                                     │   │
          │    │  ┌──────────────┐ ┌──────────────┐  │   │
          │    └──│ CLAUDE CODE  │ │CLAUDE PROJECT │──┘   │
          │       │   task       │ │   task        │      │
          │       │ (GID: ...04) │ │ (GID: ...06)  │      │
          │       └──────────────┘ └──────────────┘       │
          └───────────────────────────────────────────────┘
                              │
                     ┌────────┴────────┐
                     │  HUMAN OPERATOR  │
                     │  (Bo / Router)   │
                     │                  │
                     │  • Drags files   │
                     │  • Pastes output │
                     │  • Confirms      │
                     └─────────────────┘
```

### Three Layers

1. **Intelligence Layer** — Two Claude instances, each specialized, each with different tools and access patterns
2. **Communication Layer** — Asana task comments with structured message format (type, priority, status tracking)
3. **Sync Layer** — Version control system with registry, cascade rules, CLI tools, and a physical sync folder that produces drag-and-drop-ready file sets

---

## 4. The Two Environments

### Claude Code (The Engine Room)

**What it is:** Claude Opus 4.6 running in a local terminal via Anthropic's Claude Code product.

**Access:** Full read/write to the local filesystem. Can run bash commands, execute scripts, manage files, and interact with APIs (Asana, web).

**Strengths:**
- Sees the entire 713-file repository
- Can run 20 parallel agents simultaneously
- Executes version control cascades, evidence scoring, file reorganization
- Runs shell scripts (`auto_version.sh`) for integrity checks and sync operations
- Best for: repo operations, evidence confidence monitoring, file management, bulk document processing, infrastructure automation

**Behavioral governance:** Controlled by `CLAUDE.md` (root authority file), `AGENTS.md` (persona definitions), `GUARDRAILS.md` (hard prohibitions), and `HOOKS.md` (pre-output pipeline).

**Session persistence:** Via files in the repo. Every session reads `CLAUDE.md` first, then checks the Asana channel for pending requests.

### Claude.ai Desktop (The War Room)

**What it is:** Claude Opus 4.6 running in Anthropic's web/desktop chat interface, inside a "Project" with custom instructions and uploaded knowledge files.

**Access:** ~35 project knowledge files (read-only reference), system memory (8 persistent slots), past conversation search, web search, Linux sandbox for file creation, MCP integrations (Asana, Gmail, Slack).

**Strengths:**
- Conversational, contextual interaction optimized for strategic thinking
- Full document creation skills (docx, pdf, xlsx, pptx)
- Past conversation search across all project chats
- Persistent memory that survives across sessions without file management
- Best for: strategic analysis, legal research, document drafting, communication drafting, stress-testing, opposing counsel simulation

**Behavioral governance:** Controlled by Project Custom Instructions (`PENNINGTON_PROJECT_INSTRUCTIONS.md`), system memory (8 slots), and project knowledge files.

**Session persistence:** Via system memory (automatic across sessions) and project knowledge (manually uploaded files).

### Why Two Environments Instead of One

Neither environment alone can do what both do together. Claude Code can't draft a professional Word document with the docx skill library. Claude.ai can't read 713 files or run a bash script. Claude Code can't search past conversations. Claude.ai can't execute a version cascade across 8 files atomically.

The dual architecture isn't a workaround — it's a genuine division of labor. The Engine Room handles operations. The War Room handles strategy. The bridge keeps them in sync.

---

## 5. The Bridge Layer — Asana

### Why Asana

Both environments have native Asana MCP integration. Both can read and write task comments via API. Asana provides timestamped, persistent, ordered message history that survives session boundaries. It's the only platform both environments can natively access without the human acting as intermediary.

### Task Architecture

Two Asana tasks serve as unidirectional communication channels:

| Task Name | GID | Write Access | Read Access |
|-----------|-----|-------------|-------------|
| `CLAUDE CODE` | `1213575903318304` | Claude Code only | Claude.ai reads |
| `CLAUDE PROJECT` | `1213575903318306` | Claude.ai only | Claude Code reads |

**Critical rule:** Each environment writes ONLY to its own task and reads ONLY the other's task. This prevents message collisions and makes the conversation direction unambiguous.

### Message Format

```
[YYYY-MM-DD HH:MM TZ] [TYPE] [PRIORITY]
Subject: <one-line description>
---
<body — concise, factual, no filler>
---
Status: OPEN | ACKNOWLEDGED | RESOLVED
```

**Message Types:**
- `SYNC` — File changes, version updates, stale file notifications
- `REQUEST` — Action needed from the other environment
- `ALERT` — Urgent: evidence change, deadline issue, red alert
- `REPORT` — Substantive output (analysis, draft, recommendation)
- `QUESTION` — Needs human input
- `ACK` — Acknowledging receipt

**Priority Levels:**
- `CRITICAL` — Blocks execution or creates exposure
- `HIGH` — Affects current phase, respond this session
- `MEDIUM` — Important but not blocking, respond within 24 hours
- `LOW` — Informational, no response required

### Startup Protocol

**Claude Code:** On every new session, reads the CLAUDE PROJECT task for pending requests from Claude.ai. Processes any OPEN messages before proceeding with new work.

**Claude.ai:** On every new session, reads the CLAUDE CODE task for pending alerts, sync notifications, and responses to prior requests.

This makes the dual-environment system persistent across sessions. A request posted at 2 AM gets processed the next time that environment starts up.

---

## 6. Version Control System

### The Problem

When Claude Code updates `EVIDENCE_CONFIDENCE_MONITOR.md` because new evidence was scored, Claude.ai's copy is now stale. But Bo doesn't know which files changed during the cascade. Without a system, stale files accumulate silently.

### The Solution — Four Files

| File | Format | Purpose |
|------|--------|---------|
| `VERSION_REGISTRY.json` | JSON | Single source of truth. Tracks every document's version, status, hash, brackets, and the `claude_ai_sync` object with 35 monitored files. |
| `VERSION_RULES.yaml` | YAML | Rules engine. Defines 7 trigger types, cascade sequences, and a `final_step` that checks if any monitored file was touched. |
| `VERSION_CONTROL.md` | Markdown | Human-readable protocol with step-by-step instructions for each cascade type. |
| `scripts/auto_version.sh` | Bash | CLI tool with 8 commands for status checking, integrity verification, sync management, and automated project-push. |

### Cascade Triggers

| Trigger | Example | Cascade Effect |
|---------|---------|---------------|
| `new-evidence` | Bo provides a witness declaration | Evidence monitor updated → confidence scores change → red alerts checked → master context updated |
| `answered` | Bo answers "trim carpenter's name is Mike" | Questions file updated → evidence monitor rescored → if threshold crossed, red alert fires |
| `court-filing-edit` | Paragraph numbering fix in VC | VC version incremented → FAC, SAC, Motion, Affidavits checked for cascade |
| `phase-change` | April 4 arrives, Phase 2 fires | Strategy doc updated → context updated → filing queue reprioritized |
| `case-law-verified` | Citation confirmed valid | Case law index updated → if it affects a count, evidence monitor rescored |
| `discovery-received` | Defendant produces documents | Evidence indexed → confidence rescored → new questions generated |
| `settlement-event` | Opposing counsel makes an offer | Settlement model updated → strategy recalculated |

Every cascade ends with a `final_step` that checks: *Did any of the 35 monitored files get touched?* If yes, the sync pipeline fires.

---

## 7. Sync Agent & Project Knowledge Pipeline

### Three Components

**1. Sync Agent** (`PROJECT_KNOWLEDGE_SYNC_AGENT.md`)
A deliberately simple downstream consumer. It does not cascade. It does not detect changes. It only asks: "After that cascade finished, were any of my 35 monitored files in the list of things that changed?" It compares file modification timestamps against the last sync timestamp using epoch-second precision.

**2. Sync Folder** (`claude_project_3-7-26/`)
A physical folder in the repo that mirrors Claude.ai's project knowledge:

```
claude_project_3-7-26/
├── SYNC_MANIFEST.md     ← Version log + instructions for Bo
├── v1/                  ← Baseline: all 35 files
├── v2/                  ← Delta: only files changed in cascade #1
├── v3/                  ← Delta: only files changed in cascade #2
└── ...
```

The `v1/` folder contains all 35 files (the baseline). Each subsequent version folder contains ONLY the files that changed in that cascade. When Bo sees a new `vN/` folder appear, he opens it, uploads those specific files to Claude.ai project knowledge (replacing old versions), and runs `mark-synced`.

**3. CLI Commands**

| Command | What It Does |
|---------|-------------|
| `bash scripts/auto_version.sh status` | Shows current version state of all files |
| `bash scripts/auto_version.sh check` | Verifies integrity, detects changes since last session |
| `bash scripts/auto_version.sh hash` | Computes MD5 hashes for tamper detection |
| `bash scripts/auto_version.sh sync-check` | Compares repo state vs. Claude.ai project knowledge |
| `bash scripts/auto_version.sh mark-synced` | Records that Bo uploaded files to Claude.ai |
| `bash scripts/auto_version.sh project-status` | Shows current sync folder version, file counts, stale count |
| `bash scripts/auto_version.sh project-push` | Creates new vN/ folder with stale files, updates manifest, posts Asana notification |
| `bash scripts/auto_version.sh new-evidence` | Guides evidence processing cascade |

### The Complete Pipeline

```
TRIGGER fires (new evidence, answered question, phase change, etc.)
    │
    ▼
VERSION_CONTROL cascade runs (updates 3-8 repo files)
    │
    ▼
final_step: sync-check (checks 35 monitored files against last sync timestamp)
    │
    ▼
project-push (creates vN/ folder with ONLY the changed files)
    │
    ▼
Asana notification posted to CLAUDE CODE task
    │
    ▼
Bo sees notification, opens vN/ folder
    │
    ▼
Bo drags files into Claude.ai project knowledge (replacing old versions)
    │
    ▼
Bo runs: bash scripts/auto_version.sh mark-synced
    │
    ▼
Registry timestamp updated. Next sync-check shows all green.
```

---

## 8. The User's Role — Human as Router

The human operator has three physical actions:

1. **Drag files** — From the sync folder to Claude.ai project knowledge when a new version appears
2. **Paste output** — Copy Claude Code output into Claude.ai chat (and vice versa) when direct context transfer is needed
3. **Confirm decisions** — Both environments surface questions and recommendations; the human makes the call

The system is designed so the human never has to figure out *which* files changed or *whether* the environments are in sync. The CLI tells you. The Asana notifications tell you. The sync folder gives you the exact files. Your job is to physically move them and make decisions — not to track state.

### What the Human Does NOT Do

- Manually compare file versions
- Remember which files were updated in which session
- Maintain a mental model of what each environment knows
- Debug sync conflicts (the system flags conflicts and asks)

---

## 9. Complete File Inventory

### Root Protocol Files (in repo root)

| File | Purpose | Who Uses It |
|------|---------|-------------|
| `CLAUDE.md` | Master behavioral rules for Claude Code | Claude Code (reads first every session) |
| `AGENTS.md` | Agent persona definitions (Strategist, Red Team, Bench) | Claude Code |
| `GUARDRAILS.md` | Hard-coded prohibitions | Claude Code |
| `HOOKS.md` | Pre-output verification pipeline | Claude Code |
| `CONTEXT.md` | Living session rebuild loader | Claude Code |
| `ASANA_COMM_PROTOCOL.md` | Inter-agent communication rules | Both (via Asana) |
| `VERSION_CONTROL.md` | Human-readable version control protocol | Claude Code |
| `VERSION_REGISTRY.json` | Single source of truth for all file versions and sync state | Claude Code (scripts read this) |
| `VERSION_RULES.yaml` | Cascade trigger definitions and rules | Claude Code (scripts read this) |
| `PROJECT_KNOWLEDGE_SYNC_AGENT.md` | Sync detection logic (downstream consumer) | Claude Code |
| `EVIDENCE_CONFIDENCE_MONITOR.md` | Evidence scoring by count and element | Both |
| `_RED_ALERTS.md` | Threshold crossing notifications | Both |
| `_QUESTIONS_FOR_BO.md` | Open questions requiring human input | Both |
| `PENNINGTON_PROJECT_INSTRUCTIONS.md` | Custom instructions for Claude.ai project | Claude.ai (also in Custom Instructions field) |
| `PENNINGTON_PROJECT_MEMORY.md` | Export of Claude.ai system memory | Both |

### Repo Folder Structure

```
CAMPENNI_CASE/
├── .claude/                    ← Agent configuration
├── 01_ACTIVE_FILINGS/          ← Current version filings (v19)
├── 02_STANDBY_WEAPONS/         ← Conditional deployment docs
├── 03_EVIDENCE/                ← All exhibits, organized by type
├── 04_CORRESPONDENCE/          ← Communications records
├── 05_BAR_COMPLAINTS/          ← Bar complaint documents
├── 06_SETTLEMENT/              ← Settlement analysis
├── 07_STRATEGY/                ← Strategy documents + master context
├── 08_DAMAGES/                 ← Damages tracking
├── 09_COURT_FORMS/             ← Court forms and templates
├── 10_DISCOVERY/               ← Discovery plan (post-filing)
├── 11_VENDOR_BALANCES/         ← Vendor balance tracking
├── 12_ARCHIVE/                 ← All legacy content (475 files)
├── 13_Possible_Conspirators/   ← Conspirator case build
├── claude_project_3-7-26/      ← Sync folder (v1/ baseline + delta folders)
├── scripts/                    ← CLI tools (auto_version.sh)
└── [21 root protocol files]
```

### Claude.ai Project Knowledge (35 files)

9 v19 filing documents (.docx), 4 strategy/chronology files, 4 protocol/verification files, 3 communications records, 3 reference documents, 2 project meta files, 9 repo operational files shared with Claude.ai, 1 comm protocol file.

---

## 10. System Requirements

### Software

| Component | Version | Purpose |
|-----------|---------|---------|
| Claude Code | Opus 4.6 | Terminal-based AI agent |
| Claude.ai Desktop | Opus 4.6 | Web/desktop chat interface with Project feature |
| Asana | Any plan with API access | Communication bridge + project management |
| Bash | 4.0+ | CLI scripts |
| Python 3 | 3.8+ | JSON parsing in scripts |
| Node.js | 18+ | Document generation (docx-js) |
| md5sum / md5 | System default | File integrity verification |

### Accounts & Access

- Anthropic account with Claude Pro/Team (for Claude.ai Projects)
- Claude Code license
- Asana account with API personal access token (PAT)
- Asana workspace with a project containing 2 dedicated communication tasks

### Configuration

- Claude Code: Asana PAT stored in environment variable or `.env` file
- Claude.ai: Asana MCP connector enabled in settings
- Both environments must have access to the same Asana project

---

## 11. Setup Guide

### Step 1: Create Asana Infrastructure

1. Create an Asana project for your matter
2. Create a section for inter-agent communication
3. Create two tasks in that section:
   - `CLAUDE CODE` — where Claude Code writes, Claude.ai reads
   - `CLAUDE PROJECT` — where Claude.ai writes, Claude Code reads
4. Note the GIDs of both tasks (visible in task URL)

### Step 2: Configure Claude Code

1. Create `CLAUDE.md` in repo root with behavioral rules, including the Asana channel section with both task GIDs
2. Create `ASANA_COMM_PROTOCOL.md` with message format, type/priority definitions, and startup protocol
3. Store Asana PAT in environment variable
4. Create `scripts/auto_version.sh` with sync commands

### Step 3: Configure Claude.ai

1. Create a Project in Claude.ai
2. Write Custom Instructions that reference the dual-environment architecture
3. Upload project knowledge files (your monitored file set)
4. Configure system memory with persistent operational rules
5. Enable Asana MCP connector

### Step 4: Initialize Version Control

1. Create `VERSION_REGISTRY.json` with all monitored files listed in `claude_ai_sync`
2. Create `VERSION_RULES.yaml` with cascade triggers and `final_step` sync check
3. Create sync folder (`claude_project_<date>/v1/`) with baseline copies of all monitored files
4. Run `auto_version.sh check` to verify integrity
5. Run `auto_version.sh sync-check` to confirm all green

### Step 5: Test the Channel

1. Post a test message from Claude.ai to the CLAUDE PROJECT task
2. Start a Claude Code session — it should read the message on startup
3. Have Claude Code post a response to the CLAUDE CODE task
4. Verify Claude.ai can read the response
5. Trigger a test cascade and verify `project-push` creates a `v2/` folder

---

## 12. How It Works — Step by Step

### Scenario: New Evidence Arrives

1. Bo tells Claude Code: "I got a witness declaration from Mike identifying Campenni's defamatory statements"
2. Claude Code fires the `new-evidence` trigger
3. Cascade runs:
   - `EVIDENCE_CONFIDENCE_MONITOR.md` updated (Count I: 85% → 93%)
   - `_RED_ALERTS.md` updated (new threshold crossing)
   - `_QUESTIONS_FOR_BO.md` updated (question #4 removed)
   - `MASTER_CONTEXT.md` updated (evidence scoreboard refreshed)
4. `final_step` fires: 4 of 35 monitored files were touched
5. `project-push` creates `claude_project_3-7-26/v2/` with those 4 files
6. `SYNC_MANIFEST.md` updated: v2, March 8, trigger: new-evidence, 4 files
7. Asana notification posted to CLAUDE CODE task
8. Bo opens `v2/`, drags 4 files into Claude.ai project knowledge
9. Bo runs `mark-synced`
10. Next time Claude.ai starts a conversation, it sees the updated evidence scores

### Scenario: Claude.ai Needs Something from Claude Code

1. Bo asks Claude.ai to draft a document that requires data from the repo
2. Claude.ai posts a REQUEST to the CLAUDE PROJECT task via Asana MCP
3. Next Claude Code session reads the request on startup
4. Claude Code processes the request, posts response to CLAUDE CODE task
5. Claude.ai reads the response on its next startup (or Bo reads it in Asana and pastes the relevant output)

### Scenario: Strategic Question That Needs Both Environments

1. Bo asks Claude.ai: "Should we add a civil conspiracy count?"
2. Claude.ai checks evidence confidence (project knowledge), analyzes legal standards (web search + knowledge), and responds with a strategic recommendation
3. Claude.ai notes: "Claude Code's evidence monitor shows conspiracy at 55%. I'd need discovery-dependent evidence to push past 75%."
4. Bo takes that analysis to Claude Code and says: "Run the conspiracy scorer with the Palmisano call debrief factored in"
5. Claude Code runs the analysis with full repo access, updates scores, and posts results to Asana
6. Bo brings the results back to Claude.ai for final strategic assessment

---

## 13. CLI Reference

```bash
# Check current state of all versioned files
bash scripts/auto_version.sh status

# Verify file integrity (detect changes since last session)
bash scripts/auto_version.sh check

# Compute MD5 hashes for tamper detection
bash scripts/auto_version.sh hash

# Compare repo state vs. Claude.ai project knowledge
bash scripts/auto_version.sh sync-check

# Record that Bo uploaded files to Claude.ai
bash scripts/auto_version.sh mark-synced

# Show sync folder version, file counts, stale count
bash scripts/auto_version.sh project-status

# Create new vN/ folder with stale files + update manifest + post Asana
bash scripts/auto_version.sh project-push

# Guide for processing new evidence
bash scripts/auto_version.sh new-evidence
```

---

## 14. Use Cases Beyond Law

DualAI is domain-agnostic. The pattern works anywhere you need:

### Software Development
- **Claude Code:** Manages the codebase, runs tests, handles CI/CD, reviews PRs, manages dependencies
- **Claude.ai:** Architects solutions, writes technical specs, drafts documentation, reviews UX flows, plans sprints
- **Sync triggers:** New feature merged, test suite results changed, dependency vulnerability detected

### Academic Research
- **Claude Code:** Manages the paper repository, runs statistical analyses, organizes citations, processes datasets
- **Claude.ai:** Writes prose, structures arguments, conducts literature review (web search), drafts grant proposals
- **Sync triggers:** New dataset processed, citation verified, section draft completed

### Business Operations
- **Claude Code:** Manages financial models, processes reports, maintains dashboards, handles data pipelines
- **Claude.ai:** Drafts investor decks, writes executive summaries, analyzes market data, prepares board materials
- **Sync triggers:** Quarterly numbers updated, new market data integrated, competitor analysis refreshed

### Creative Production
- **Claude Code:** Manages asset files, version-controls scripts, tracks production schedules, handles file conversions
- **Claude.ai:** Writes scripts, develops characters, provides creative direction, drafts pitch materials
- **Sync triggers:** Script revision completed, asset inventory updated, production schedule changed

### Healthcare / Clinical
- **Claude Code:** Manages patient data pipelines (anonymized), processes lab results, maintains protocol databases
- **Claude.ai:** Drafts clinical protocols, analyzes treatment outcomes, writes reports, prepares regulatory submissions
- **Sync triggers:** New trial data processed, protocol updated, regulatory requirement changed

### The General Pattern

Any domain where you need:
1. **Deep file system operations** AND **strategic thinking** on the same project
2. **Persistent state** across sessions in both environments
3. **Deterministic sync** so neither environment operates on stale data
4. **Asynchronous communication** that survives session boundaries
5. **Human oversight** at decision points without human overhead on logistics

---

## 15. Limitations & Known Constraints

### Inherent to the Architecture

- **Human in the loop for file transfer.** The sync folder produces the files; the human must physically upload them to Claude.ai. There is no automated upload path today.
- **Asana message size limit.** Comments are capped at ~2000 characters. Complex handoffs require file references rather than inline content.
- **Claude.ai project knowledge cap.** ~35 files is a practical limit. The monitored file list must be curated — not everything in the repo can be synced.
- **Session boundary.** Neither Claude environment remembers the other's conversation. Context must be passed through files, memory, or Asana messages.
- **Latency.** A request posted by Claude.ai is not seen by Claude Code until the next Claude Code session starts. This is asynchronous by design, but means real-time collaboration is not possible.

### Operational

- **Version drift risk** if the human forgets to run `mark-synced` after uploading files. The system will flag the same files as stale again on the next cascade.
- **Claude.ai system memory is limited** (8 slots currently). Critical operational rules must fit in these slots; everything else goes in project knowledge.
- **Claude Code sessions are ephemeral.** CLAUDE.md must be read first every session. No behavioral state persists except what's written to files.

---

## 16. Design Philosophy

### Deliberately Dumb Components

The sync agent doesn't think. It compares two timestamps. The sync folder doesn't decide — it copies files. All intelligence lives in the version control cascade (VERSION_RULES.yaml) and the two Claude instances. The infrastructure components are simple, predictable, and impossible to get wrong.

### Single Source of Truth

`VERSION_REGISTRY.json` is the one file that tracks everything: document versions, file statuses, sync state, monitored file list, and last sync timestamp. Every script, every agent, every check reads from this file. There is no second copy and no hardcoded list that can drift.

### One-Way Communication Channels

Each Asana task is unidirectional. Claude Code writes to one, Claude.ai writes to the other. There is no ambiguity about who said what or where to look for responses.

### Human as Router, Not Bottleneck

The system tells the human exactly what to do: "Upload these 4 files." "Run this command." "Answer this question." The human doesn't debug, doesn't diff, doesn't track. The human decides and moves.

### Defense in Depth

Claude Code has four layers of behavioral control: CLAUDE.md (root authority), AGENTS.md (persona rules), GUARDRAILS.md (hard prohibitions), HOOKS.md (pre-output pipeline). Even if one file is missed, the others catch violations. Claude.ai has three layers: Custom Instructions, system memory, and project knowledge files — each reinforcing the same rules.

### Zero Deletion Policy

Files are never deleted. They are moved to archive. Every version is preserved. Every cascade is logged. If something goes wrong, the full history is recoverable.

---

## Confidentiality

**CONFIDENTIAL — PRO SE WORK PRODUCT**

This document and all referenced files, task GIDs, case details, and system architecture are proprietary to Bo Pennington / Pentek Design Build LLC. No portion of this document may be shared, distributed, or reproduced without express written authorization.

---

*DualAI v1.0 — Built March 7, 2026*
*Bo Pennington + Claude (Anthropic)*
