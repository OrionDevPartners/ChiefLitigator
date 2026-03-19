# Ciphergy Pipeline Enhancements: v0 to v1

This document details every enhancement made in the evolution from the original case-specific implementation (v0) to the domain-agnostic Ciphergy Pipeline (v1).

---

## 1. Architecture

### Domain-Agnostic Design

**Before (v0):** Hardcoded file paths, case-specific logic, single-use structure.
**Now (v1):** All project-specific details live in `config/ciphergy.yaml`. The engine reads config at runtime and adapts to any domain.
**Why it matters:** One codebase serves legal, startup, medical, or any custom project type. No code changes needed for new domains.

### Config-Driven Behavior

**Before (v0):** Behavior embedded in scripts. Changing a cascade rule meant editing bash.
**Now (v1):** Cascade rules, agent definitions, sync settings, and dashboard config all live in YAML. Modify `ciphergy.yaml` to change system behavior without touching code.
**Why it matters:** Non-developers can customize the pipeline. Configuration is declarative and auditable.

### Template System

**Before (v0):** Single set of markdown files with case-specific content.
**Now (v1):** Domain templates define default files, alert formats, and question formats. Four built-in domains (custom, legal, startup, medical) with extensible template structure.
**Why it matters:** New projects start with appropriate scaffolding for their domain, reducing setup time.

---

## 2. Version Control

### Python Cascade Engine

**Before (v0):** Bash functions with limited error handling and no step isolation.
**Now (v1):** Full Python cascade engine (`cascade.py`) with:
  - Named steps that execute in priority order
  - Shared context object for inter-step data passing
  - Per-step error handling with cascade halt on failure
  - Audit logging of all cascade executions
**Why it matters:** Cascades are reliable, debuggable, and extensible. New steps are Python functions, not bash hacks.

### Dynamic File Lists from Registry

**Before (v0):** Hardcoded list of monitored files in the bash script.
**Now (v1):** File tracking driven entirely by `.ciphergy/registry.json`. The registry is populated at init time by scanning the project, and updated dynamically as files are added.
**Why it matters:** No manual file list maintenance. Add a file to the project and it gets tracked automatically on the next cascade.

---

## 3. Sync Pipeline

### Automated project-push

**Before (v0):** Manual copying of files to version folders.
**Now (v1):** `ciphergy.sh project-push` automatically:
  1. Compares current hashes against synced hashes
  2. Identifies stale and new files
  3. Creates a versioned delta folder (sync/vN/)
  4. Copies only changed files
  5. Updates version history in registry
**Why it matters:** Zero manual effort to prepare uploads. No risk of missing changed files.

### Delta Versioning

**Before (v0):** Full copies of all files in each version folder.
**Now (v1):** Only changed files are included in delta versions. The registry tracks which files changed and why.
**Why it matters:** Smaller uploads, faster syncs, clear audit trail of what changed per version.

### Hash-Based Change Detection

**Before (v0):** Timestamp-based or manual change tracking.
**Now (v1):** MD5 hashes computed for every tracked file. Sync state determined by hash comparison, not timestamps.
**Why it matters:** Reliable detection of actual content changes. Touching a file without changing it does not trigger a false positive.

---

## 4. CLI

### 10 Commands vs 6

**Before (v0):** 6 commands: status, check, hash, sync-check, mark-synced, project-push.
**Now (v1):** 10 commands:
  - `status` -- Project state overview
  - `check` -- Integrity verification
  - `hash` -- Hash computation
  - `sync-check` -- Repo vs cloud comparison
  - `mark-synced` -- Record sync event
  - `project-status` -- Sync folder and version history
  - `project-push` -- Create delta version
  - `cascade` -- Run cascade engine
  - `init` -- Initialize new project
  - `help` -- Command reference
**Why it matters:** Complete workflow coverage from a single tool. No need to run Python scripts directly for standard operations.

### Init Command

**Before (v0):** Manual setup of config files and directories.
**Now (v1):** `ciphergy.sh init --name "Project" --domain legal` creates the entire project scaffolding including config, registry, sync baseline, templates, and Asana validation.
**Why it matters:** New projects are ready in seconds. No manual file creation or directory setup.

### Cascade Command

**Before (v0):** Cascades were implicit (you just edited files and ran sync).
**Now (v1):** Explicit cascade execution with typed triggers: `ciphergy.sh cascade new-evidence`. Each trigger runs a defined sequence of steps.
**Why it matters:** Consistent, repeatable response to events. The system handles the ripple effects so you do not have to remember what to update.

---

## 5. Asana Integration

### Python Wrapper

**Before (v0):** Raw curl commands for Asana API calls.
**Now (v1):** `AsanaBridge` class with:
  - `read_messages(task_gid)` -- Fetch all comments
  - `post_message(task_gid, message)` -- Post formatted comment
  - `get_pending(task_gid)` -- Filter for unresolved messages
  - `format_message()` -- Structured message builder
**Why it matters:** Type-safe, tested API wrapper replaces fragile shell commands. Retry logic handles rate limits and transient errors.

### Retry Logic

**Before (v0):** Single attempt. Failure = manual retry.
**Now (v1):** 3 retries with exponential backoff. Respects Asana's Retry-After header for rate limits. Distinguishes between retryable (5xx, 429) and non-retryable (4xx) errors.
**Why it matters:** Resilient communication. Transient API issues do not block the pipeline.

### Message Formatting

**Before (v0):** Plain text messages with no structure.
**Now (v1):** Structured format with type tags ([STATUS], [ALERT], etc.), priority levels (P0-P3), timestamps, and consistent signatures.
**Why it matters:** Messages are parseable by both humans and automated systems. Priority levels enable filtering and triage.

---

## 6. Dashboard (NEW)

**Before (v0):** No visual interface. CLI-only.
**Now (v1):** Flask web dashboard (`dashboard.py` + `index.html`) providing:
  - Project status overview with color-coded stats
  - File registry table with sync state badges
  - Agent status display
  - Version history timeline
  - RED alert display
  - Auto-refresh every 30 seconds
**Why it matters:** Visual monitoring without terminal access. Shareable with team members. Quick status checks without running commands.

---

## 7. Templates (NEW)

**Before (v0):** One-size-fits-all file structure.
**Now (v1):** Domain-specific templates for:
  - **Legal:** RED alerts, questions, timeline, evidence index, strategy
  - **Startup:** RED alerts, questions, roadmap, metrics
  - **Medical:** RED alerts, questions, patient timeline, treatment log
  - **Custom:** RED alerts, questions (minimal)
**Why it matters:** Projects start with domain-appropriate structure. Templates encode best practices for each domain.

---

## 8. Security

### PAT in Config Not Code

**Before (v0):** Asana PAT sometimes hardcoded or stored in config files checked into git.
**Now (v1):** PAT stored in environment variable. Config file references the variable name, not the value. Config file is gitignored.
**Why it matters:** No credential exposure in version control. Standard secrets management practice.

### Gitignore for Sensitive Files

**Before (v0):** Minimal or no gitignore.
**Now (v1):** Comprehensive `.gitignore` excludes:
  - `.ciphergy/registry.json` (contains file hashes)
  - `config/ciphergy.yaml` (may contain GIDs)
  - `sync/v*/` (contains project file copies)
  - `.env` (environment files)
  - `__pycache__/`, `*.pyc`, `node_modules/`
**Why it matters:** Sensitive data, large files, and build artifacts stay out of version control.

---

## 9. Documentation

### 4 Documents vs 1

**Before (v0):** Single README with everything crammed in.
**Now (v1):** Four dedicated documents:
  1. `ARCHITECTURE.md` -- System design, data flows, ASCII diagrams
  2. `SETUP_GUIDE.md` -- Installation, configuration, verification
  3. `USER_GUIDE.md` -- Daily workflow, triggers, best practices
  4. `API_REFERENCE.md` -- Complete reference for all scripts, configs, and schemas
**Why it matters:** Right information in the right place. Setup guide for onboarding, user guide for daily work, API reference for development.

### Schema Documentation

**Before (v0):** No formal schema definitions.
**Now (v1):** Complete JSON and YAML schemas documented in API_REFERENCE.md for:
  - `ciphergy.yaml` configuration file
  - `.ciphergy/registry.json` registry file
  - Asana message format
**Why it matters:** Developers and integrators know exactly what data structures to expect and produce.

---

## 10. Multi-Domain Support

### Domain Templates

**Before (v0):** Built for one specific use case.
**Now (v1):** Four built-in domain templates with distinct file scaffolding, alert formats, and question templates.
**Why it matters:** The same tool works for a legal case, a startup launch, a medical study, or any custom project.

### Examples

**Legal project:**
```bash
ciphergy.sh init --name "Smith v. Jones" --domain legal
# Creates: _RED_ALERTS.md, _QUESTIONS.md, _TIMELINE.md, _EVIDENCE_INDEX.md, _STRATEGY.md
```

**Startup project:**
```bash
ciphergy.sh init --name "Product Launch" --domain startup
# Creates: _RED_ALERTS.md, _QUESTIONS.md, _ROADMAP.md, _METRICS.md
```

**Medical project:**
```bash
ciphergy.sh init --name "Clinical Study" --domain medical
# Creates: _RED_ALERTS.md, _QUESTIONS.md, _PATIENT_TIMELINE.md, _TREATMENT_LOG.md
```

---

## Summary

| Category | v0 | v1 | Improvement |
|----------|----|----|-------------|
| Architecture | Hardcoded, single-use | Config-driven, domain-agnostic | Reusable platform |
| Version Control | Manual file lists | Dynamic registry + Python engine | Automated, reliable |
| Sync Pipeline | Manual copy | Auto delta versioning | Zero-effort sync |
| CLI | 6 commands | 10 commands + init + cascade | Complete workflow |
| Asana | Raw curl | Python wrapper + retry + formatting | Resilient, structured |
| Dashboard | None | Flask web UI | Visual monitoring |
| Templates | None | 4 domain templates | Quick start |
| Security | Minimal | PAT in env, gitignore, hash integrity | Production-grade |
| Documentation | 1 README | 4 dedicated docs + schemas | Professional |
| Multi-Domain | Single case | Legal, startup, medical, custom | Universal tool |

---
*Ciphergy Pipeline --- Enhancement Log*
