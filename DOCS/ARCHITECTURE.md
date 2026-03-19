# Ciphergy Pipeline Architecture

## System Overview

Ciphergy Pipeline is a domain-agnostic dual-environment AI orchestration platform. It manages the knowledge synchronization between a local development environment and a cloud-based AI agent, ensuring both environments maintain consistent, versioned project state.

```
+---------------------------------------------------------------+
|                     Ciphergy Pipeline                            |
|                                                                |
|  +------------------+    Sync    +------------------+          |
|  |  LOCAL AGENT     |  -------> |  CLOUD AGENT     |          |
|  |  (CLI + Scripts) |  <------- |  (AI Platform)   |          |
|  +------------------+           +------------------+          |
|         |                              |                       |
|         v                              v                       |
|  +------------------+           +------------------+          |
|  |  File System     |           |  Project Context |          |
|  |  Registry        |           |  Knowledge Base  |          |
|  +------------------+           +------------------+          |
|         |                              |                       |
|         +----------+  +---------------+                        |
|                    |  |                                         |
|                    v  v                                         |
|              +------------------+                              |
|              |  Asana Comm Bus  |                              |
|              +------------------+                              |
+---------------------------------------------------------------+
```

## Three-Layer Architecture

### Layer 1: Behavioral Layer

The behavioral layer defines HOW the system processes information and makes decisions.

```
+---------------------------------------------------+
|              BEHAVIORAL LAYER                      |
|                                                    |
|  Cascade Engine    File Registry    Sync Pipeline  |
|       |                |                |          |
|  Triggers         MD5 Hashes       Delta Versions  |
|  Priority Rules   Categories       Manifests       |
|  Step Execution   Version History  Upload Tracking  |
+---------------------------------------------------+
```

**Components:**
- **Cascade Engine** (`cascade.py`): Processes trigger events and cascades updates through the file system in priority order.
- **File Registry** (`.ciphergy/registry.json`): Tracks all monitored files, their hashes, categories, and sync state.
- **Sync Pipeline**: Manages versioned snapshots for upload to the cloud agent.

### Layer 2: Operational Layer

The operational layer provides the tools and interfaces for day-to-day use.

```
+---------------------------------------------------+
|              OPERATIONAL LAYER                     |
|                                                    |
|  CLI (ciphergy.sh)                                   |
|    |-- status        |-- sync-check               |
|    |-- check         |-- mark-synced              |
|    |-- hash          |-- project-status           |
|    |-- cascade       |-- project-push             |
|    |-- init          |-- help                     |
|                                                    |
|  Dashboard (dashboard.py)                          |
|    |-- Status Overview                             |
|    |-- File Registry Table                         |
|    |-- Sync State                                  |
|    |-- RED Alerts                                  |
|                                                    |
|  Init Engine (ciphergy_init.py)                      |
|    |-- Config Generation                           |
|    |-- Registry Creation                           |
|    |-- Template Scaffolding                        |
+---------------------------------------------------+
```

**Components:**
- **CLI** (`ciphergy.sh`): 10-command bash interface for all pipeline operations.
- **Dashboard** (`dashboard.py` + `index.html`): Web-based status visualization.
- **Init Engine** (`ciphergy_init.py`): Project scaffolding and initialization.

### Layer 3: Communication Layer

The communication layer handles inter-agent messaging and external integrations.

```
+---------------------------------------------------+
|              COMMUNICATION LAYER                   |
|                                                    |
|  Asana Bridge (asana_bridge.py)                    |
|    |-- read_messages()                             |
|    |-- post_message()                              |
|    |-- get_pending()                               |
|    |-- format_message()                            |
|                                                    |
|  Message Types:                                    |
|    STATUS | ALERT | QUESTION | ANSWER              |
|    DIRECTIVE | CASCADE | SYNC | INFO               |
|                                                    |
|  Priority Levels:                                  |
|    P0 (CRITICAL) | P1 (HIGH)                       |
|    P2 (MEDIUM)   | P3 (LOW)                        |
+---------------------------------------------------+
```

**Components:**
- **Asana Bridge** (`asana_bridge.py`): Structured API wrapper with retry logic and message formatting.

## Data Flow

### Cascade Flow

```
Trigger Event (e.g., new-evidence)
       |
       v
  Read cascade rules from config
       |
       v
  Execute steps in priority order:
       |
       +---> update_registry
       +---> recompute_hashes
       +---> check_alerts
       +---> sync_check (always last)
       |
       v
  Update registry version history
       |
       v
  (Optional) Create delta version
       |
       v
  (Optional) Post Asana notification
```

### Sync Flow

```
Local file changes detected
       |
       v
  ciphergy.sh sync-check
       |
       v
  Compare current hashes vs synced hashes
       |
       +---> [All match] --> "In sync"
       +---> [Differences] --> "Stale files found"
                |
                v
          ciphergy.sh project-push
                |
                v
          Create sync/vN/ with changed files
                |
                v
          Human uploads vN/ to cloud agent
                |
                v
          ciphergy.sh mark-synced
                |
                v
          Registry updated with current hashes
```

### Init Flow

```
ciphergy.sh init --name "Project" --domain legal
       |
       v
  Create/load config/ciphergy.yaml
       |
       v
  Generate domain-specific templates
       |
       v
  Scan project files --> .ciphergy/registry.json
       |
       v
  Create sync/v1/ baseline
       |
       v
  Create SYNC_MANIFEST.md
       |
       v
  Validate Asana connection (if configured)
       |
       v
  Post init message to Asana (if connected)
```

## Cascade Mechanics

Cascades are the core update mechanism. When something changes in the project, a cascade propagates that change through all dependent files and systems.

### Trigger Types

| Trigger | Priority | Description | Default Steps |
|---------|----------|-------------|---------------|
| new-evidence | P1 | New data added | registry, hashes, alerts, sync |
| answered | P2 | Question resolved | questions, impacts, sync |
| phase-change | P1 | Phase transition | registry, hashes, integrity, sync |
| deadline | P0 | Deadline event | alerts, escalate, sync |
| correction | P1 | Error correction | registry, hashes, log, sync |
| escalation | P0 | Priority escalation | alerts, asana, sync |

### Step Execution

Steps execute sequentially. Each step receives a shared context object containing:
- `trigger`: The trigger type
- `trigger_file`: Optional file path that caused the trigger
- `project_root`: Absolute path to project
- `config`: Parsed YAML config
- `registry`: Parsed JSON registry (mutated in place)
- `files_changed`: Running count of changed files

If any step fails, the cascade halts and reports the error.

## Security Model

### Secrets Management
- Asana PAT stored in environment variable (never in config files)
- Config file (`ciphergy.yaml`) is in `.gitignore`
- Registry (`.ciphergy/registry.json`) is in `.gitignore`
- Sync version folders (`sync/v*/`) are in `.gitignore`

### Access Control
- Local agent has full filesystem access
- Cloud agent receives only explicitly synced files
- Asana bridge uses token-based authentication with retry logic
- No credentials stored in code or version control

### Data Integrity
- MD5 hashes for all tracked files
- Hash comparison on every sync check
- Version history with full audit trail
- Cascade log records all automated changes

## File Structure

```
CIPHERGY_PIPELINE/
  config/
    ciphergy.yaml           # Project configuration (gitignored)
  .ciphergy/
    registry.json          # File tracking registry (gitignored)
  scripts/
    ciphergy.sh              # Main CLI tool
    ciphergy_init.py         # Project initializer
    cascade.py             # Cascade execution engine
    asana_bridge.py        # Asana API wrapper
  sync/
    SYNC_MANIFEST.md       # Upload instructions
    v1/                    # Baseline version (gitignored)
    v2/                    # Delta version (gitignored)
  dashboard/
    dashboard.py           # Flask web dashboard
    index.html             # Dashboard frontend
  docs/
    ARCHITECTURE.md        # This file
    SETUP_GUIDE.md         # Installation guide
    USER_GUIDE.md          # Daily usage guide
    API_REFERENCE.md       # Script and config reference
  templates/               # Domain-specific templates
  _RED_ALERTS.md           # Active alerts
  _QUESTIONS.md            # Open questions
  requirements.txt         # Python dependencies
  package.json             # Node dependencies
  .gitignore               # Git exclusions
  LICENSE                  # Proprietary license
  ENHANCEMENTS.md          # Changelog from v0 to v1
```

---
*Ciphergy Pipeline --- Architecture Document*
