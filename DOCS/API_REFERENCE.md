# Ciphergy Pipeline API Reference

## CLI Commands (ciphergy.sh)

### status

Show current project state including agent status, file counts, and sync state.

```bash
ciphergy.sh status
```

**Output includes:**
- Project name and domain
- Total tracked files and missing file count
- Current sync version and last sync timestamp
- Agent names and statuses (color-coded)

**Requires:** config, registry

---

### check

Verify project integrity. Checks that all tracked files exist, validates config and registry format, and compares stored hashes against actual file hashes.

```bash
ciphergy.sh check
```

**Output includes:**
- Per-file existence check (FOUND/MISS)
- Config YAML validation (OK/FAIL)
- Registry JSON validation (OK/FAIL)
- Per-file hash comparison (MATCH/STALE/NEW)

**Exit codes:**
- `0` -- All checks passed
- `1` -- One or more issues found

**Requires:** config, registry

---

### hash

Compute MD5 hashes for all tracked files and update the registry.

```bash
ciphergy.sh hash
```

**Output includes:**
- Per-file hash with status (COMPUTED/UPDATED/UNCHANGED)
- Count of hashes updated

**Side effects:** Updates `.ciphergy/registry.json` with new hashes.

**Requires:** config, registry

---

### sync-check

Compare current repository state against the cloud agent's known state (last sync snapshot).

```bash
ciphergy.sh sync-check
```

**Output includes:**
- Per-file sync state (SYNCED/STALE/NEW)
- Summary counts
- Action recommendation if out of sync

**Requires:** config, registry

---

### mark-synced

Record that the human has uploaded current files to the cloud agent. Snapshots all current file hashes as the "synced" baseline.

```bash
ciphergy.sh mark-synced
```

**Output includes:**
- Number of files marked as synced
- Timestamp of sync record

**Side effects:** Updates `sync.synced_hashes` and `sync.last_synced` in registry.

**Requires:** config, registry

---

### project-status

Display sync folder state and version history.

```bash
ciphergy.sh project-status
```

**Output includes:**
- Sync folder contents (version folders and file counts)
- Last 10 entries from version history

**Requires:** config, registry

---

### project-push

Create a delta version folder containing only files that changed since the last sync.

```bash
ciphergy.sh project-push
```

**Output includes:**
- List of files copied to the new version folder
- Version number and file count

**Side effects:**
- Creates `sync/vN/` folder with changed files
- Updates `version_history` and `sync.current_version` in registry

**Requires:** config, registry

---

### cascade

Run a cascade triggered by a specific event type.

```bash
ciphergy.sh cascade <trigger>
```

**Arguments:**
- `trigger` (required) -- One of: `new-evidence`, `answered`, `phase-change`, `deadline`, `correction`, `escalation`

**Delegates to:** `scripts/cascade.py`

**Requires:** config, registry

---

### init

Initialize a new Ciphergy project.

```bash
ciphergy.sh init [--name "Project Name"] [--domain custom|legal|startup|medical]
```

**Arguments:**
- `--name` -- Project name (prompted if not provided)
- `--domain` -- Project domain template (default: `custom`)

**Delegates to:** `scripts/ciphergy_init.py`

---

### help

Display help text with all available commands, triggers, and examples.

```bash
ciphergy.sh help
```

---

## ciphergy_init.py

### Usage

```bash
python scripts/ciphergy_init.py --name "Project Name" --domain <domain> [--project-root /path]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--name` | Yes | -- | Project name |
| `--domain` | No | `custom` | Domain template: `custom`, `legal`, `startup`, `medical` |
| `--project-root` | No | Auto-detected | Root directory of the project |

### What It Creates

1. `config/ciphergy.yaml` -- Project configuration (if not existing)
2. `.ciphergy/registry.json` -- File tracking registry
3. `sync/v1/` -- Baseline version folder with all tracked files
4. `sync/SYNC_MANIFEST.md` -- Upload instructions
5. `_RED_ALERTS.md` -- Domain-specific alert template
6. `_QUESTIONS.md` -- Domain-specific questions template

### Asana Integration

If Asana is configured and enabled in `ciphergy.yaml`:
- Validates the PAT by calling `GET /users/me`
- Posts an initialization message to the configured comm task

---

## cascade.py

### Usage

```bash
python scripts/cascade.py --trigger <trigger> [--file <path>] [--project-root /path]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--trigger` | Yes | -- | Cascade trigger type |
| `--file` | No | `""` | File that triggered the cascade |
| `--project-root` | No | Auto-detected | Root directory of the project |

### Trigger Types

| Trigger | Priority | Steps |
|---------|----------|-------|
| `new-evidence` | 1 | update_registry, recompute_hashes, check_alerts, sync_check |
| `answered` | 2 | update_questions, check_cascading_impacts, sync_check |
| `phase-change` | 1 | update_registry, recompute_hashes, full_integrity_check, sync_check |
| `deadline` | 0 | check_alerts, escalate_open_items, sync_check |
| `correction` | 1 | update_registry, recompute_hashes, log_correction, sync_check |
| `escalation` | 0 | update_alerts, notify_asana, sync_check |

### Custom Triggers

Add new triggers in `config/ciphergy.yaml` under `cascades`:

```yaml
cascades:
  my-custom-trigger:
    description: "Description of the trigger"
    priority: 2
    steps:
      - update_registry
      - recompute_hashes
      - sync_check
```

### Available Steps

| Step Name | Description |
|-----------|-------------|
| `update_registry` | Scans for new files and adds them to the registry |
| `recompute_hashes` | Recalculates MD5 hashes for all tracked files |
| `check_alerts` | Reads `_RED_ALERTS.md` and counts active alerts |
| `update_alerts` | Placeholder for custom alert update logic |
| `update_questions` | Checks `_QUESTIONS.md` status |
| `check_cascading_impacts` | Analyzes if the change triggers further updates |
| `full_integrity_check` | Verifies all tracked files exist on disk |
| `escalate_open_items` | Reviews open items for escalation |
| `log_correction` | Records a correction event in the registry |
| `notify_asana` | Posts a notification to the configured Asana task |
| `sync_check` | Compares local state vs synced state (run last) |

### Exit Codes

- `0` -- Cascade completed successfully
- `1` -- Cascade failed or unknown trigger

---

## asana_bridge.py

### Class: AsanaBridge

#### Constructor

```python
bridge = AsanaBridge(config_path="config/ciphergy.yaml", pat=None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_path` | `str` | `None` | Path to ciphergy.yaml |
| `pat` | `str` | `None` | Asana PAT (overrides config) |

#### read_messages(task_gid)

Get all comments from an Asana task.

```python
messages = bridge.read_messages("1234567890")
# Returns: [{"id": "...", "author": "...", "text": "...", "created_at": "...", "type": "..."}]
```

**Returns:** `list[dict]` with keys: `id`, `author`, `text`, `created_at`, `type`

#### post_message(task_gid, message)

Post a comment to an Asana task.

```python
result = bridge.post_message("1234567890", "Hello from Ciphergy")
# Returns: {"gid": "...", ...}
```

**Returns:** `dict` -- The created story data from Asana API

#### get_pending(task_gid)

Get unresolved messages (QUESTION, ALERT, DIRECTIVE types not followed by ANSWER/RESOLVED).

```python
pending = bridge.get_pending("1234567890")
# Returns: [{"id": "...", "text": "...", "type": "QUESTION", ...}]
```

**Returns:** `list[dict]` -- Pending messages only

#### format_message(msg_type, priority, subject, body, status) [static]

Build a formatted Ciphergy message string.

```python
msg = AsanaBridge.format_message(
    msg_type="STATUS",
    priority="HIGH",
    subject="Sync Complete",
    body="All 15 files uploaded to cloud agent.",
    status="DONE"
)
```

**Returns:** `str` -- Formatted message

### CLI Usage

```bash
# Read messages
python scripts/asana_bridge.py read --task-gid 1234567890

# Post simple message
python scripts/asana_bridge.py post --task-gid 1234567890 --message "Hello"

# Post formatted message
python scripts/asana_bridge.py post --task-gid 1234567890 \
  --message "Body text" \
  --formatted --type STATUS --priority HIGH --subject "Subject"

# Check pending messages
python scripts/asana_bridge.py pending --task-gid 1234567890
```

---

## Configuration Schema (ciphergy.yaml)

```yaml
project:
  name: string          # Project name (required)
  domain: string        # Domain: custom|legal|startup|medical
  version: string       # Semantic version
  created: string       # ISO 8601 timestamp

agents:
  <agent_name>:
    name: string        # Display name
    type: string        # Agent type: cli|cloud|api
    status: string      # Status: active|idle|offline

asana:
  enabled: boolean      # Enable Asana integration
  pat_env_var: string   # Environment variable name for PAT
  workspace_gid: string # Asana workspace GID
  project_gid: string   # Asana project GID
  comm_task_gid: string # Asana task GID for communication

cascades:
  <trigger_name>:
    description: string # Human-readable description
    priority: integer   # 0 = highest, 5 = lowest
    steps: list         # Ordered list of step names

sync:
  auto_push: boolean    # Auto-create delta on cascade
  sync_dir: string      # Sync folder path (relative)
  manifest: string      # Manifest file path (relative)

dashboard:
  port: integer         # Dashboard HTTP port
  auto_refresh_seconds: integer  # Dashboard refresh interval
```

---

## Registry Schema (.ciphergy/registry.json)

```json
{
  "project": {
    "name": "string",
    "domain": "string",
    "initialized": "ISO 8601 timestamp"
  },
  "files": [
    {
      "path": "relative/path/to/file",
      "hash": "md5 hex digest",
      "tracked_since": "ISO 8601 timestamp",
      "category": "script|document|data|configuration|dashboard|template|other"
    }
  ],
  "agents": {
    "<agent_name>": {
      "status": "active|idle|offline",
      "type": "cli|cloud|api",
      "last_active": "ISO 8601 timestamp"
    }
  },
  "sync": {
    "current_version": "vN",
    "last_synced": "ISO 8601 timestamp | never",
    "synced_hashes": {
      "relative/path": "md5 hex digest"
    }
  },
  "version_history": [
    {
      "version": "vN",
      "date": "ISO 8601 timestamp",
      "trigger": "string",
      "files_changed": 0,
      "files": ["list of paths"]
    }
  ],
  "cascade_log": [
    {
      "trigger": "string",
      "date": "ISO 8601 timestamp",
      "files_changed": 0,
      "success": true
    }
  ],
  "corrections": [
    {
      "date": "ISO 8601 timestamp",
      "trigger_file": "string",
      "note": "string"
    }
  ]
}
```

---
*Ciphergy Pipeline --- API Reference*
