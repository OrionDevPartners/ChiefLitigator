# COMM PROTOCOL -- Asana Message Bus

> **Ciphergy Pipeline v1.0**
> Purpose: Structured communication between AGENT LOCAL and AGENT CLOUD via Asana
> Transport: Asana task comments (two-task architecture)

---

## 1. Architecture

The Ciphergy Pipeline uses **two Asana tasks** as a bidirectional message bus:

```
AGENT LOCAL                          AGENT CLOUD
    |                                     |
    |--- writes to LOCAL OUTBOX --------->|  (AGENT CLOUD reads)
    |                                     |
    |<------- writes to CLOUD OUTBOX -----|  (AGENT LOCAL reads)
    |                                     |
```

| Task | GID Config Key | Writer | Reader |
|------|---------------|--------|--------|
| AGENT LOCAL Outbox | `asana.agent_local_task_gid` | AGENT LOCAL | AGENT CLOUD |
| AGENT CLOUD Outbox | `asana.agent_cloud_task_gid` | AGENT CLOUD | AGENT LOCAL |

Each agent writes **only** to its own outbox. Each agent reads **only** from the other agent's outbox.

---

## 2. Message Format

Every message posted to Asana must follow this format:

```
[YYYY-MM-DD HH:MM UTC] [TYPE] [PRIORITY]
SUBJECT: [Brief description]
---
[Message body]
---
REF: [File paths, task IDs, or "None"]
```

### Message Types

| Type | Code | Usage |
|------|------|-------|
| Synchronization | `SYNC` | File changed, hash updated, version bumped |
| Request | `REQUEST` | Asking the other agent to do something |
| Alert | `ALERT` | Something is wrong or needs immediate attention |
| Report | `REPORT` | Delivering results, analysis, or completed work |
| Question | `QUESTION` | Asking for information or clarification |
| Acknowledgment | `ACK` | Confirming receipt or completion |

### Priority Levels

| Priority | Code | Expected Response Time |
|----------|------|----------------------|
| Critical | `CRITICAL` | Immediate (next read cycle) |
| High | `HIGH` | Within current session |
| Medium | `MEDIUM` | Within 24 hours |
| Low | `LOW` | When convenient |

---

## 3. Trigger Table

### AGENT LOCAL Posts When:

| Trigger | Type | Priority | Content |
|---------|------|----------|---------|
| Session started | ACK | LOW | "Session started, config loaded" |
| Monitored file changed | SYNC | MEDIUM | File path, old hash, new hash |
| Task completed | REPORT | MEDIUM | Summary of what was done |
| Needs strategic input | REQUEST | HIGH | Specific question + context |
| Error encountered | ALERT | HIGH/CRITICAL | Error details, affected files |
| Confidence threshold breach | ALERT | HIGH | Claim, score, threshold |
| Version registry updated | SYNC | LOW | Files updated, new versions |
| Human provided new input | SYNC | MEDIUM | Summary of input (not raw content) |
| Cascade completed | REPORT | LOW | Cascade summary |
| File conflict detected | ALERT | CRITICAL | Conflicting files, details |

### AGENT CLOUD Posts When:

| Trigger | Type | Priority | Content |
|---------|------|----------|---------|
| Session started | ACK | LOW | "Session started, knowledge loaded" |
| Research complete | REPORT | MEDIUM | Findings + crosscheck block |
| Document draft ready | SYNC | MEDIUM | Draft content for LOCAL to save |
| Strategic recommendation | REPORT | HIGH | Recommendation + WDC cert |
| Contradiction found | ALERT | HIGH | Both conflicting sources |
| Needs file content | REQUEST | MEDIUM | File path needed |
| Needs command executed | REQUEST | HIGH | Exact command + purpose |
| Question for human | QUESTION | varies | Question + context |
| Risk identified | ALERT | HIGH/CRITICAL | Risk description + mitigation |
| Answering LOCAL's question | REPORT | matches original | Answer + crosscheck |

---

## 4. API Usage

### Using curl (AGENT LOCAL)

**Read messages from AGENT CLOUD outbox:**

```bash
curl -s "https://app.asana.com/api/1.0/tasks/[CLOUD_TASK_GID]/stories" \
  -H "Authorization: Bearer [ASANA_PAT]" \
  -H "Accept: application/json" | jq '.data[] | select(.type == "comment") | {created_at, text}'
```

**Post message to AGENT LOCAL outbox:**

```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks/[LOCAL_TASK_GID]/stories" \
  -H "Authorization: Bearer [ASANA_PAT]" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "text": "[YYYY-MM-DD HH:MM UTC] [TYPE] [PRIORITY]\nSUBJECT: [Description]\n---\n[Body]\n---\nREF: [References]"
    }
  }'
```

**Check for new messages since last read:**

```bash
curl -s "https://app.asana.com/api/1.0/tasks/[CLOUD_TASK_GID]/stories?opt_fields=created_at,text,type" \
  -H "Authorization: Bearer [ASANA_PAT]" | \
  jq --arg since "[LAST_READ_TIMESTAMP]" \
  '.data[] | select(.type == "comment" and .created_at > $since) | {created_at, text}'
```

### Using MCP (if configured)

```
Tool: asana_post_comment
Parameters:
  task_gid: [YOUR_OUTBOX_TASK_GID]
  text: "[FORMATTED_MESSAGE]"

Tool: asana_get_comments
Parameters:
  task_gid: [OTHER_AGENT_OUTBOX_TASK_GID]
  since: [LAST_READ_TIMESTAMP]  (optional)
```

---

## 5. Communication Guardrails

### Never Post Raw File Content

- Asana comments have practical character limits and are not designed for full documents
- Summarize changes and reference file paths instead
- If AGENT CLOUD needs file content, AGENT LOCAL should paste relevant excerpts (not entire files)
- Maximum recommended message length: **4,000 characters**

### Never Post Sensitive Data

- No API keys, tokens, passwords, or secrets in Asana comments
- No personally identifiable information unless required by the project domain
- Reference secret names (e.g., "the Asana PAT") rather than values

### Message Threading

- When responding to a specific message, reference it by timestamp:
  `RE: [ORIGINAL_TIMESTAMP] [ORIGINAL_TYPE]`
- Keep related exchanges in the same task -- do not create new tasks for threads
- If a thread exceeds 10 exchanges on the same topic, create a summary REPORT

### Deduplication

- Before posting, check if the same message was already posted (same type + subject within last hour)
- Do not re-post ACKs for the same event
- SYNC messages for the same file within 5 minutes should be consolidated

---

## 6. Polling & Timing

### AGENT LOCAL (session-based)

- Check AGENT CLOUD outbox on **every session startup**
- Check again **before every major action** (file write, cascade, etc.)
- Check again **before session end**

### AGENT CLOUD (session-based)

- Check AGENT LOCAL outbox on **every session startup**
- Check again **before every substantive output**
- Check again **before session end**

### Staleness

- Messages older than 7 days without an ACK are considered stale
- Stale CRITICAL or HIGH messages should trigger an ALERT on next read
- Stale LOW or MEDIUM messages are logged but do not trigger alerts

---

## 7. Error Recovery

| Error | Response |
|-------|----------|
| Asana API returns 401 | PAT may be expired -- post ALERT locally, notify human |
| Asana API returns 429 | Rate limited -- backoff 60s, retry up to 3x |
| Asana API returns 5xx | Server error -- backoff 30s, retry up to 5x |
| Message post fails | Save message locally to `sync/pending_messages.json`, retry next cycle |
| Cannot read outbox | Log locally, continue with available context, retry next cycle |

### Pending Message Queue

If Asana is unreachable, messages are queued locally:

```json
{
  "pending_messages": [
    {
      "timestamp": "[ISO_TIMESTAMP]",
      "target_task_gid": "[TASK_GID]",
      "message": "[FORMATTED_MESSAGE]",
      "retry_count": 0,
      "max_retries": 5
    }
  ]
}
```

On next successful connection, flush the queue in chronological order.

---

*The Asana message bus is the sole communication channel between agents. All cross-agent coordination flows through this protocol.*
