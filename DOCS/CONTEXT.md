# CIPHERGY — CONTEXT

## What Is Ciphergy?

Ciphergy is a **signal extraction platform** for complex adversarial domains. It coordinates two independent AI environments through a shared message bus, with automated evidence scoring, entity analysis, deadline tracking, cascading document updates, quality-gated outputs, and adversarial review panels.

Born March 7, 2026. Forged in a real fight. Works in any fight.

**Cipher** (noun): A key that turns noise into signal.
**Energy** (noun): The force you bring to the battle.
**Ciphergy** = Cipher + Energy.

## The Problem It Solves

Anyone fighting a complex battle with incomplete information faces the same challenges:
- Data scattered across documents, emails, messages, records
- No single source of truth for what you can prove and what's missing
- Deadlines that get buried when you're focused on something else
- Communications that need to be precise under adversarial scrutiny
- Two brains (local execution + cloud strategy) that can't talk to each other
- Documents that become stale when new intelligence arrives

Ciphergy solves all of these with a unified automation layer.

## Architecture

```
┌──────────────┐       ┌─────────┐       ┌──────────────┐
│ AGENT LOCAL   │◄─────►│   BUS   │◄─────►│ AGENT CLOUD  │
│ (Execution)   │       │ (Asana) │       │ (Strategy)   │
│ Files, shell, │       │         │       │ Memory, web, │
│ cascade engine│       │ 2 tasks │       │ persistence  │
└──────┬───────┘       └────┬────┘       └──────┬───────┘
       │                    │                    │
       │              ┌─────┴─────┐              │
       │              │   HUMAN   │              │
       │              │  (Bridge) │              │
       │              └───────────┘              │
       │                                         │
       ▼                                         ▼
┌──────────────────────────────────────────────────┐
│              CIPHERGY NERVOUS SYSTEM              │
│                                                   │
│  nerve_center.py ── Cascade Engine                │
│  agent_comm.py ── Inter-Agent Bus                 │
│  5 AI Agents ── Mesh Intelligence                 │
│  Domain Profiles ── Vocabulary Plugins            │
│  Quality Gates ── Output Filtering                │
│  Confidence Monitor ── Hypothesis Scoring         │
│  Milestone Tracker ── Deadline Sentinel           │
│  DIFF/ ── Audit Trail                             │
└──────────────────────────────────────────────────┘
```

## The 5 AI Agents (The Mesh)

| Agent | Role | Trigger |
|-------|------|---------|
| **Onboarding Agent** | Guides user from zero to operational | First session / "set up" |
| **Evidence Coach** | Scores data, identifies gaps | New data uploaded |
| **Deadline Sentinel** | Always watching milestones | Every session startup |
| **Draft Guardian** | 7-gate filter on outbound comms | Any outbound draft |
| **Strategy Advisor** | Three Moves Ahead on every decision | Decision points |

## Domains

Ciphergy is domain-agnostic. The engine is the same. The vocabulary changes.

| Domain | Entity | Hypothesis | Adversary | Discipline |
|--------|--------|-----------|-----------|-----------|
| Legal | Person of Interest | Claim / Count | Opposing Counsel | Glacier Mode |
| Medical | Patient / Provider | Diagnosis | Insurance / Reviewer | Clinical Precision |
| Investigation | Subject / POI | Intel Assessment | Threat Actor | OPSEC |
| Engineering | Component / Vendor | Failure Mode | Inspector / Adjuster | Engineering Rigor |
| Default | Entity | Hypothesis | Adversary | Professional Precision |
