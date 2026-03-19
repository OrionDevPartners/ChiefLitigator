# Cyphergy
Ciphergy decodes the legal system. It transforms the dense, impenetrable world of litigation — statutes, rules, deadlines, evidence standards, jurisdictional traps — into clear strategy, court-ready documents &amp; actionable next steps. 7 AI agents work as one integrated legal team, turning complexity into clarity for anyone.

# CIPHERGY

### Decode the Law. Prosecute with Clarity.

> **Ciphergy** decodes the legal system. It transforms the dense, impenetrable world of litigation — statutes, rules, deadlines, evidence standards, jurisdictional traps — into clear strategy, court-ready documents & actionable next steps. 7 AI agents work as one integrated legal team, turning complexity into clarity for anyone.

```
STATUS:     PRIVATE — PROPRIETARY — COMMERCIAL
PROVIDER:   AWS Bedrock / Bedrock Core Agents
FRONTEND:   Cloudflare Pages
BACKEND:    AWS ECS Fargate
CI/CD:      GitHub Actions
DATABASE:   Neon Serverless Postgres → AWS Aurora
```

---

## Table of Contents

- [What Is Ciphergy](#what-is-ciphergy)
- [Architecture](#architecture)
- [The Seven Agents](#the-seven-agents)
- [LLM Engine — AWS Bedrock](#llm-engine--aws-bedrock)
- [Infrastructure Stack](#infrastructure-stack)
- [Connector Framework](#connector-framework)
- [Quick Start](#quick-start)
- [File Structure](#file-structure)
- [Prompt Stack](#prompt-stack)
- [Supported Practice Areas](#supported-practice-areas)
- [Data Sources & APIs](#data-sources--apis)
- [Workflows](#workflows)
- [Case Portability](#case-portability)
- [Deployment](#deployment)
- [Security & Ethics](#security--ethics)
- [Development Workflow](#development-workflow)

---

## What Is Ciphergy

Ciphergy is a **multi-agentic AI-powered legal co-counsel platform** that gives any pro se litigant the full operational capability of a well-staffed litigation team.

It is not a single prompt. It is an integrated system of:

- **Specialized prompt modules** that mount onto AWS Bedrock foundation models
- **Bedrock Core Agents** orchestrating seven specialized legal personas
- **Connector interfaces** that bind to external tools and services
- **Data extraction protocols** that ensure zero-loss portability
- **Workflow directives** that execute end-to-end litigation processes

Ciphergy handles the complete lifecycle of any legal matter — from pre-suit investigation through post-judgment enforcement — in any U.S. state, any federal district, any appellate circuit, and any specialized tribunal.

### Core Properties

| Property | Description |
|---|---|
| **Jurisdiction-Agnostic** | No default state. Identifies correct jurisdiction on intake, adapts all terminology, rules, and analysis. |
| **Multi-Agentic** | Seven specialized virtual agents orchestrated through Bedrock Core Agents. |
| **Model-Agnostic within Bedrock** | Agent-to-model mapping is configurable. Swap foundation models per agent without code changes. |
| **Tool-Integrated** | Modular connector layer binds to external services (Drive, Calendar, Asana, Slack, etc.). |
| **Portable** | 22-section extraction protocol transfers 100% of case data between any environment. |
| **Self-Auditing** | Flags confidence levels, verifies citations, stress-tests its own work product. |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     CLOUDFLARE PAGES                         │
│                 (Static Frontend — Global Edge)               │
│           React/Vite · Zero egress · WAF · DDoS              │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    AWS ECS FARGATE                            │
│              (Backend API — FastAPI / Node.js)                │
│          Zero-downtime rolling deploys via GitHub Actions     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               AWS BEDROCK CORE AGENTS                   │ │
│  │            (Multi-Agent Orchestration Layer)             │ │
│  │                                                         │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐            │ │
│  │  │ Lead      │ │ Research  │ │ Drafting   │            │ │
│  │  │ Strategist│ │ Agent     │ │ Agent      │            │ │
│  │  └───────────┘ └───────────┘ └───────────┘            │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐            │ │
│  │  │ Procedural│ │ Evidence  │ │ Opposing   │            │ │
│  │  │ Agent     │ │ Agent     │ │ Counsel Sim│            │ │
│  │  └───────────┘ └───────────┘ └───────────┘            │ │
│  │  ┌───────────┐                                        │ │
│  │  │ Judgment  │  Model Pool:                           │ │
│  │  │ Agent     │  Claude (Bedrock) · Llama · Titan      │ │
│  │  └───────────┘  Mistral · Cohere · [swappable]        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ AWS Secrets   │  │ Neon Postgres │  │ S3 / Case    │      │
│  │ Manager       │  │ → Aurora      │  │ File Storage │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                    CONNECTOR LAYER                            │
│  Google Drive · Gmail · Calendar · Asana · Slack · Zapier    │
│  DocuSign · S&P Global · Notion · Airtable · [extensible]   │
└──────────────────────────────────────────────────────────────┘
```

### Four Layers

| Layer | What | Where |
|---|---|---|
| **Prompt Stack** | Agent instructions, workflows, extraction protocols | Git repo → Bedrock Agent configs |
| **Connectors** | Modular tool interfaces | Fargate API ↔ external services |
| **Data Sources** | Legal databases, court systems, public records | Web APIs + user uploads + S3 |
| **Output Engine** | .docx pleadings, .pdf memos, calendar events, Asana tasks | Fargate → Cloudflare → user |

---

## The Seven Agents

Each agent maps to a Bedrock Core Agent with its own prompt, tools, and configurable foundation model.

| # | Agent | Domain | Bedrock Model (Default) | Swap Candidates |
|---|---|---|---|---|
| 1 | **Lead Strategist** | Case theory, risk, settlement, appellate preservation, agent coordination | Claude Sonnet (Bedrock) | Claude Opus, Llama 3.1 405B |
| 2 | **Legal Research** | Statutes, case law, jurisdictional surveys, citation verification | Claude Opus (Bedrock) | Claude Sonnet, Mistral Large |
| 3 | **Drafting** | All litigation documents — pleadings, motions, discovery, briefs | Claude Opus (Bedrock) | Claude Sonnet, Llama 3.1 405B |
| 4 | **Procedural & Compliance** | Filing rules, service, deadlines, e-filing, fees, standing orders | Claude Sonnet (Bedrock) | Mistral Large, Claude Haiku |
| 5 | **Evidence & Discovery** | Admissibility, authentication, hearsay, privilege, expert standards | Claude Sonnet (Bedrock) | Claude Opus, Cohere Command R+ |
| 6 | **Opposing Counsel Sim** | Defense anticipation, stress testing, cross-exam prep | Claude Opus (Bedrock) | Llama 3.1 405B, Claude Sonnet |
| 7 | **Judgment & Enforcement** | Collection, garnishment, liens, asset discovery, domestication | Claude Sonnet (Bedrock) | Mistral Large, Claude Haiku |

### Agent-Model Configuration

```yaml
# config/agents.yaml — Swap models without touching prompts or code

agents:
  lead_strategist:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
    max_tokens: 4096
    temperature: 0.3
    tools: [web_search, file_storage, task_management, calendar]

  legal_research:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-opus-20240229-v1:0
    max_tokens: 8192
    temperature: 0.1
    tools: [web_search, knowledge_base]

  drafting:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-opus-20240229-v1:0
    max_tokens: 8192
    temperature: 0.2
    tools: [web_search, file_storage]

  procedural_compliance:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
    max_tokens: 4096
    temperature: 0.1
    tools: [web_search, calendar, task_management]

  evidence_discovery:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
    max_tokens: 4096
    temperature: 0.2
    tools: [file_storage, database]

  opposing_counsel_sim:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-opus-20240229-v1:0
    max_tokens: 8192
    temperature: 0.4
    tools: [web_search]

  judgment_enforcement:
    prompt: prompts/base_prompt_v1.md
    bedrock_model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
    max_tokens: 4096
    temperature: 0.2
    tools: [web_search, financial_data]
```

**To swap a model**: Change `bedrock_model_id` in the config. No prompt edits. No code changes. The agent inherits the same personality, tools, and workflow — just runs on different hardware.

---

## LLM Engine — AWS Bedrock

All inference runs through **AWS Bedrock** or **Bedrock Core Agents**. No direct API calls to any external LLM provider. Everything stays inside your AWS account.

| Benefit | Why It Matters |
|---|---|
| **Single billing** | All model costs flow through your existing AWS account |
| **Data residency** | Prompts and case data never leave your AWS region |
| **Model swapping** | Change foundation models per-agent with one config line |
| **Multi-agent orchestration** | Bedrock Core Agents handles routing, memory, and tool use |
| **Guardrails** | Bedrock Guardrails for content filtering and PII redaction |
| **Logging** | CloudWatch integration for all inference calls |
| **Compliance** | SOC 2, HIPAA-eligible, FedRAMP — AWS handles the audits |

### Available Foundation Models (Bedrock)

```
anthropic.claude-3-opus-*          # Highest reasoning — Research, Drafting, OpCo Sim
anthropic.claude-3-5-sonnet-*      # Best balance — Strategist, Procedural, Evidence
anthropic.claude-3-haiku-*         # Fast/cheap — Deadline computation, simple lookups
meta.llama3-1-405b-instruct-*      # Open weights alternative — stress testing, bulk
mistral.mistral-large-*            # European alternative — regulatory analysis
cohere.command-r-plus-*            # RAG-optimized — knowledge base queries
amazon.titan-text-*                # AWS native — fallback, cost optimization
```

---

## Infrastructure Stack

### Production

| Layer | Technology | Why |
|---|---|---|
| **Frontend Host** | Cloudflare Pages | Zero egress, global edge, WAF, DDoS protection |
| **Backend Host** | AWS ECS Fargate | Serverless containers, zero-downtime deploys |
| **LLM Engine** | AWS Bedrock / Bedrock Core Agents | Model agnostic within Bedrock, single billing |
| **Database** | Neon Serverless Postgres → AWS Aurora | Start cheap, scale seamlessly |
| **Secrets** | AWS Secrets Manager | Injected at container boot, never in code |
| **File Storage** | AWS S3 | Case files, evidence, work product |
| **Logging** | AWS CloudWatch | All inference, API calls, errors |
| **CI/CD** | GitHub Actions | Automated build, test, deploy on merge to main |
| **DNS / CDN** | Cloudflare | SSL, caching, edge routing |
| **Container Registry** | AWS ECR | Private Docker image storage |

### Development Workflow

```
[ TO BE DETERMINED ]
```

---

## Connector Framework

Connectors are modular interfaces. Each defines a **capability contract** — not an implementation. The backend resolves which provider fulfills each capability at runtime from environment config.

### Tier 1 — Critical

| Connector Interface | Capability | Default Provider |
|---|---|---|
| `file_storage` | Case file repository, document search, version comparison | Google Drive → S3 |
| `email` | Correspondence search, draft composition, communication tracking | Gmail |
| `calendar` | Deadline tracking, hearing dates, multi-reminder alerts | Google Calendar |
| `task_management` | Litigation phase tracking, discovery management, action items | Asana |
| `messaging` | Context search, status updates, team coordination | Slack |
| `web_search` | Citation verification, current law research, court info | Bedrock Agent tool |

### Tier 2 — High Value

| Connector Interface | Capability | Default Provider |
|---|---|---|
| `knowledge_base` | Legal research wiki, case law notes, cross-matter reference | Notion |
| `automation` | PACER alert routing, cross-platform triggers | Zapier |
| `document_signing` | Settlement execution, contract signature tracking | DocuSign |
| `financial_data` | Corporate research, damages data, asset discovery | S&P Global |
| `visual_design` | Timelines, relationship diagrams, evidence maps | Figma |

### Tier 3 — Specialized

| Connector Interface | Capability | Default Provider |
|---|---|---|
| `database` | Evidence tracking, witness lists, exhibit logs | Airtable → Postgres |
| `legal_ai` | Specialized legal research | Harvey (Bedrock connector) |
| `version_control` | Document version tracking | GitHub |
| `deployment` | Case status dashboards | Cloudflare Pages |

### Adding a New Connector

```
connectors/
├── interfaces/           # Capability contracts (provider-independent)
│   ├── file_storage.py
│   ├── email.py
│   └── ...
├── bindings/             # Provider-specific implementations
│   ├── google_drive.py
│   ├── gmail.py
│   ├── s3.py
│   └── ...
└── registry.py           # Resolves interface → binding at runtime
```

---

## Quick Start

```bash
# 1. Clone
git clone git@github.com:[org]/ciphergy.git
cd ciphergy

# 2. Configure
cp .env.example .env
nano .env

# 3. Install
pip install -r requirements.txt

# 4. Run locally
uvicorn app.main:app --reload --port 8000

# 5. Deploy
git push origin main   # GitHub Actions handles the rest
```

---

## File Structure

```
ciphergy/
├── README.md
├── .env.example
├── .gitignore
├── Dockerfile
│
├── prompts/
│   ├── base_prompt_v1.md
│   ├── amendment_1.0.md
│   ├── extraction_prompt.md
│   └── README.md
│
├── config/
│   ├── agents.yaml
│   ├── connectors.yaml
│   └── guardrails.yaml
│
├── app/
│   ├── main.py
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── lead_strategist.py
│   │   ├── legal_research.py
│   │   ├── drafting.py
│   │   ├── procedural.py
│   │   ├── evidence.py
│   │   ├── opposing_counsel.py
│   │   └── enforcement.py
│   ├── connectors/
│   │   ├── interfaces/
│   │   ├── bindings/
│   │   └── registry.py
│   ├── workflows/
│   │   ├── intake.py
│   │   ├── complaint_defense.py
│   │   ├── motion_practice.py
│   │   ├── discovery.py
│   │   ├── trial_prep.py
│   │   └── case_transfer.py
│   ├── documents/
│   │   ├── docx_builder.py
│   │   ├── pdf_builder.py
│   │   └── templates/
│   └── utils/
│       ├── deadline_calculator.py
│       ├── citation_verifier.py
│       └── confidence_flagger.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── wrangler.toml
│   ├── package.json
│   └── vite.config.ts
│
├── case_structure/
│   ├── 01-Pleadings/
│   ├── 02-Motions/
│   ├── 03-Discovery/
│   ├── 04-Depositions/
│   ├── 05-Correspondence/
│   ├── 06-Court-Orders/
│   ├── 07-Evidence/
│   ├── 08-Research-Memos/
│   ├── 09-Trial-Preparation/
│   ├── 10-Settlement/
│   └── 11-Administrative/
│
├── .github/workflows/
│   ├── deploy-cloudflare.yml
│   └── deploy-fargate.yml
│
├── .aws/
│   └── task-def.json
│
├── docs/
│   ├── runbook.md
│   ├── connector_guide.md
│   ├── bedrock_setup.md
│   └── security.md
│
└── scripts/
    ├── setup.sh
    ├── extract.sh
    └── validate_connectors.sh
```

---

## Prompt Stack

| Document | Sections | Purpose | Mount Order |
|---|---|---|---|
| **Base Prompt v1.0** | I–IX | Core identity, 7 agents, jurisdictional adaptability, practice areas, capabilities, ethics | First |
| **Amendment 1.0** | X–XX | Tool directives, document processing, deadlines, expanded practice areas, error correction, risk framework | Second |
| **Extraction Prompt** | 1–22 | Zero-loss case data mining from any session | On demand |

---

## Supported Practice Areas

**Primary**: Construction Law · Real Estate Law · Plaintiff's Torts · Contract Law · Insurance Law · Business Law

**Extended**: Family Law · Intellectual Property · Tax Disputes · Probate & Successions · Environmental Law · Immigration (Civil)

**Cross-Jurisdictional**: Federal Civil Rights (§ 1983) · Employment Law · Bankruptcy · Administrative Law · ADR · Judgment Enforcement

---

## Data Sources & APIs

### Free / Open Access

| Source | URL | Use Case |
|---|---|---|
| Google Scholar | scholar.google.com | Case law, legal journals |
| Cornell LII | law.cornell.edu | Federal statutes, CFR, UCC |
| CourtListener | courtlistener.com | Federal opinions, docket tracking |
| Congress.gov | congress.gov | Federal legislation |
| SEC EDGAR | sec.gov/edgar | Corporate filings |
| PACER | pacer.uscourts.gov | Federal court dockets |
| State SOS Sites | [varies] | Entity searches, registered agents |
| County Recorders | [varies] | Property records, liens |

### Paid (Manual Verification)

Westlaw · LexisNexis · Bloomberg Law · Fastcase · Harvey · vLex — No direct integration. System provides exact search terms for manual verification.

---

## Workflows

```
1. NEW MATTER INTAKE
   Facts → Jurisdiction ID → Quick-Reference Card → Claims Explorer
   → Prescription check → Checklist → Asana project → Calendar → Assessment

2. COMPLAINT DEFENSE
   Upload → Full read → Analysis → Answer deadline → Draft Answer
   → Opposing Counsel Sim → Discovery strategy → Deadline calendar

3. MOTION PRACTICE
   Research (3+) → Draft Motion + Memo → Stress test → Revise
   → Proposed Order → Certificate of Service → Filing instructions

4. DISCOVERY PACKAGE
   Analyze claims → Interrogatories → RFPs → RFAs
   → Deposition Notices → Asana tracking → Calendar deadlines

5. TRIAL PREPARATION
   Witness list → Exhibit list → Motions in limine → Jury instructions
   → Opening/closing frameworks → Cross-exam prep

6. CASE TRANSFER
   Paste Extraction Prompt → 22-section extraction → Copy to new env
   → Ingest + confirm → Transfer Readiness Assessment
```

---

## Case Portability

22-section zero-loss extraction: Executive Summary · Parties & Entities · Complete Timeline · Claims Analysis · Defenses & Opposition · Stress Testing · Evidence Inventory · Discovery Status · Motions & Proceedings · Legal Research · Work Product · Strategy · Communications · Financials · Jurisdiction & Procedure · Insurance · Open Questions · Action Items · Lessons Learned · Raw Data Dump · Verification Checklist · Transfer Assessment

---

## Deployment

### Frontend → Cloudflare Pages

```yaml
# .github/workflows/deploy-cloudflare.yml
# Triggers on push to main → builds React/Vite → deploys to Cloudflare Pages
```

**Required GitHub Secrets**: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`

### Backend → AWS ECS Fargate

```yaml
# .github/workflows/deploy-fargate.yml
# Triggers on push to main → builds Dockerfile → pushes to ECR → updates ECS
# Zero-downtime rolling deploy
```

**Required GitHub Secrets**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

**Required AWS Resources**: ECR repository · ECS cluster + service · IAM roles (execution + task with Secrets Manager + Bedrock access) · CloudWatch log group · Secrets Manager vault

### Bedrock Setup

```
Enable in AWS Console → Bedrock → Model Access:
  - Anthropic Claude 3 Opus
  - Anthropic Claude 3.5 Sonnet
  - Anthropic Claude 3 Haiku
  - Meta Llama 3.1 405B (optional)
  - Mistral Large (optional)

Fargate task role IAM policy must include:
  - bedrock:InvokeModel
  - bedrock:InvokeModelWithResponseStream
  - bedrock:InvokeAgent
  - bedrock:Retrieve
```

---

## Security & Ethics

### Ethical Boundaries

1. Never fabricates citations or legal authority
2. Never advises conduct violating professional rules, court rules, or law
3. Never sends communications without explicit user confirmation
4. Recommends attorney consultation for high-stakes matters
5. Reminds users about non-privileged nature of AI communications

### Data Security

| Control | Implementation |
|---|---|
| **Secrets** | AWS Secrets Manager — injected at boot, never in code |
| **Encryption at rest** | S3 SSE, RDS encryption, Bedrock encrypted storage |
| **Encryption in transit** | TLS everywhere — Cloudflare → Fargate → Bedrock |
| **PII handling** | Bedrock Guardrails PII redaction |
| **Access control** | IAM least-privilege, per-service task roles |
| **Logging** | CloudWatch for all API and inference calls |
| **Data residency** | All case data stays in configured AWS region |

### Confidence Protocol

| Level | Flag | Meaning |
|---|---|---|
| **High** | None | Verified, established, clear statutory text |
| **Moderate** | `[Verify]` | May have been amended or differ by jurisdiction |
| **Low** | `[UNVERIFIED]` | Research before relying on it |

---

## Development Workflow

```
[ TO BE DETERMINED ]
```

---

**PROPRIETARY AND CONFIDENTIAL**
*All rights reserved. Unauthorized reproduction, distribution, or use is strictly prohibited.*

*Cipher + Energy = Ciphergy — the force that decrypts the law and puts it to work.*
