# Ciphergy Pipeline User Guide

## Daily Workflow

The typical daily workflow follows this pattern:

```
1. Check status       -->  ciphergy status
2. Review alerts      -->  Check _RED_ALERTS.md
3. Do your work       -->  Edit project files
4. Run cascade        -->  ciphergy cascade <trigger>
5. Check sync state   -->  ciphergy sync-check
6. Push delta         -->  ciphergy project-push
7. Upload to cloud    -->  Manual upload of sync/vN/
8. Mark synced        -->  ciphergy mark-synced
```

### Morning Routine

```bash
# 1. Check overall project health
ciphergy status

# 2. Check integrity
ciphergy check

# 3. Review sync state
ciphergy sync-check

# 4. Open dashboard for visual overview
python dashboard/dashboard.py &
```

### After Making Changes

```bash
# 1. Run appropriate cascade
ciphergy cascade new-evidence

# 2. Check what needs syncing
ciphergy sync-check

# 3. Create delta version
ciphergy project-push

# 4. Upload the new version folder to your cloud agent

# 5. Mark as synced
ciphergy mark-synced
```

## Responding to Triggers

### New Evidence

When new data, documents, or information arrives:

```bash
# Add the file to your project directory
cp /path/to/new_document.pdf ./evidence/

# Run the new-evidence cascade
ciphergy cascade new-evidence

# The cascade will:
# 1. Detect the new file and add it to the registry
# 2. Recompute all hashes
# 3. Check if any RED alerts need updating
# 4. Run a final sync check
```

### Answering a Question

When you resolve an open question:

1. Update `_QUESTIONS.md` -- change the status from OPEN to ANSWERED
2. Add the answer and date
3. Run the cascade:

```bash
ciphergy cascade answered
```

### Phase Change

When the project transitions to a new phase:

```bash
ciphergy cascade phase-change
```

This runs a full integrity check in addition to the standard registry and hash updates.

### Deadline Events

When a deadline is approaching or has been reached:

```bash
ciphergy cascade deadline
```

This checks alerts and escalates any open items.

### Corrections

When you need to correct an error in existing data:

```bash
ciphergy cascade correction
```

This logs the correction event for audit purposes.

### Escalation

When something needs priority escalation:

```bash
ciphergy cascade escalation
```

This updates alerts and posts an Asana notification.

## Managing Cascades

### Custom Cascade Rules

Edit `config/ciphergy.yaml` to customize cascade behavior:

```yaml
cascades:
  new-evidence:
    description: "New data or documents added"
    priority: 1
    steps:
      - update_registry
      - recompute_hashes
      - check_alerts
      - notify_asana     # Add this to get Asana notifications
      - sync_check       # Always keep this last
```

### Available Steps

| Step | What It Does |
|------|-------------|
| `update_registry` | Scans for new files, adds to registry |
| `recompute_hashes` | Recalculates MD5 for all tracked files |
| `check_alerts` | Reads _RED_ALERTS.md for active alerts |
| `update_alerts` | Placeholder for custom alert logic |
| `update_questions` | Checks _QUESTIONS.md state |
| `check_cascading_impacts` | Analyzes if changes trigger further updates |
| `full_integrity_check` | Verifies all tracked files exist |
| `escalate_open_items` | Reviews items that need escalation |
| `log_correction` | Records correction in audit log |
| `notify_asana` | Posts notification to Asana task |
| `sync_check` | Compares local vs cloud state (always run last) |

## Uploading to Cloud Agent

### Manual Upload Process

1. Run `ciphergy project-push` to create a delta version folder
2. Navigate to `sync/vN/` (where N is the latest version number)
3. Upload all files in that folder to your cloud agent project
4. After upload, run `ciphergy mark-synced`

### What Gets Uploaded

Only files that have changed since the last sync are included in delta versions. The sync system tracks this via MD5 hashes.

### Verifying Upload

After uploading and marking as synced:

```bash
ciphergy sync-check
```

All files should show as "SYNCED" (green).

## Reading Asana Messages

### From the CLI

```bash
# Read all messages
python scripts/asana_bridge.py read --task-gid YOUR_TASK_GID

# Check pending (unresolved) messages
python scripts/asana_bridge.py pending --task-gid YOUR_TASK_GID
```

### Posting Messages

```bash
# Simple message
python scripts/asana_bridge.py post --task-gid YOUR_TASK_GID --message "Update complete"

# Formatted message
python scripts/asana_bridge.py post --task-gid YOUR_TASK_GID \
  --message "All files synced to v3" \
  --formatted \
  --type STATUS \
  --priority MEDIUM \
  --subject "Sync Complete"
```

### Message Format

Ciphergy uses a structured message format:

```
[TYPE] PRIORITY | Subject
Time: 2026-03-07 14:30 UTC

Message body here.

Status: Complete

--- Ciphergy Pipeline
```

## Handling RED Alerts

### Alert File Format

`_RED_ALERTS.md` uses a markdown table:

```markdown
# RED ALERTS

| # | Alert | Severity | Status | Date Raised |
|---|-------|----------|--------|-------------|
| 1 | Missing critical document | HIGH | OPEN | 2026-03-07 |
| 2 | Deadline in 48 hours | CRITICAL | OPEN | 2026-03-07 |
```

### Responding to Alerts

1. Review the alert in `_RED_ALERTS.md`
2. Take the required action
3. Update the alert status to RESOLVED
4. Run `ciphergy cascade correction` or the appropriate trigger
5. Sync to cloud agent

### Adding New Alerts

Manually add rows to the alert table:

```markdown
| 3 | New issue description | HIGH | OPEN | 2026-03-07 |
```

Or use an escalation cascade:

```bash
ciphergy cascade escalation
```

## Tips and Best Practices

### 1. Always Sync After Changes
Run `ciphergy sync-check` after any significant work to see what the cloud agent is missing.

### 2. Use Cascades, Not Manual Updates
Let cascades handle registry updates and hash recomputation. They ensure consistency.

### 3. Keep Alerts Current
Stale alerts reduce trust in the system. Resolve or update alerts promptly.

### 4. Review the Dashboard
The web dashboard provides a quick visual snapshot. Keep it open during work sessions.

### 5. Version History Is Your Audit Trail
The registry's version history and cascade log track everything. Use `ciphergy project-status` to review.

### 6. One Trigger Per Event
Run one cascade per distinct event. If you add evidence AND answer a question, run both cascades:

```bash
ciphergy cascade new-evidence
ciphergy cascade answered
```

### 7. Customize for Your Domain
Edit `config/ciphergy.yaml` to add domain-specific cascade steps, change priorities, or add new trigger types.

### 8. Back Up Your Registry
While the registry is gitignored (it contains hashes), consider periodic backups:

```bash
cp .ciphergy/registry.json .ciphergy/registry.backup.json
```

### 9. Check Integrity Weekly
Run `ciphergy check` at least weekly to catch any drift:

```bash
ciphergy check
```

### 10. Keep the Cloud Agent Updated
The longer you go without syncing, the more the cloud agent's knowledge diverges. Sync at least daily during active work.

---
*Ciphergy Pipeline --- User Guide*
