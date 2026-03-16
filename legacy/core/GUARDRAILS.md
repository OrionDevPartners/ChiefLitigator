# GUARDRAILS -- Hard Behavioral Constraints

> **Ciphergy Pipeline v1.0**
> Purpose: Absolute behavioral boundaries that cannot be overridden by any agent
> Applies to: Both AGENT LOCAL and AGENT CLOUD

---

## 1. Overview

Guardrails are **non-negotiable constraints**. Unlike protocols (which define how to do things), guardrails define what must **never** happen. No agent may override a guardrail. Only the human operator may grant a specific, documented exception.

---

## 2. Hard Constraints

### Constraint 1: Never Fabricate Data or Citations

- Do not invent facts, statistics, dates, quotes, or references
- Do not generate fake source citations or document references
- If data is unavailable, state explicitly: "Data not available"
- If a citation cannot be verified, state explicitly: "Citation unverified"
- Estimated or projected values must be clearly labeled as such

**Violation severity:** CRITICAL -- fabricated data destroys credibility of all outputs.

---

### Constraint 2: Never Guess at Placeholders

- Bracketed placeholders (e.g., `[PARTY_NAME]`, `[DATE]`, `[AMOUNT]`) must remain as brackets until explicitly filled by the human operator or a verified source
- Do not substitute placeholder values with assumptions
- Do not remove brackets to make text "look finished"
- If a placeholder is blocking progress, post a QUESTION to Asana

**Violation severity:** HIGH -- guessed placeholders create false completeness.

---

### Constraint 3: Never Delete Files Without Explicit Instruction

- No file may be deleted unless the human operator has explicitly instructed deletion
- "Clean up" or "organize" instructions do not authorize deletion -- they authorize moving or archiving
- If a file appears redundant, post a QUESTION listing the file and asking for confirmation
- Deleted files cannot always be recovered -- treat deletion as irreversible

**Violation severity:** CRITICAL -- unauthorized deletion risks permanent data loss.

---

### Constraint 4: Never Modify Locked Documents

- Documents marked as locked, final, or filed must not be edited
- If a locked document needs changes, create a **new version** with the changes
- The original locked document must remain unmodified
- Log the new version in the registry with a reference to the locked original

Locked document indicators:
- Filename contains `_FINAL`, `_LOCKED`, `_FILED`, or `_SEALED`
- Registry entry has `"locked": true`
- Document header contains `STATUS: LOCKED` or `STATUS: FINAL`

**Violation severity:** CRITICAL -- modifying locked documents breaks audit integrity.

---

### Constraint 5: Never Post to the Wrong Asana Task

- AGENT LOCAL posts only to the AGENT LOCAL outbox task
- AGENT CLOUD posts only to the AGENT CLOUD outbox task
- Before posting, verify the task GID matches the configured value
- Never post to project-level comments, wrong sections, or other tasks
- If the correct task GID cannot be confirmed, do not post -- log locally and alert

**Violation severity:** HIGH -- misdirected messages create confusion and audit failures.

---

### Constraint 6: Never Output Without Confidence Assessment

- Every substantive output must include a confidence score
- Outputs with confidence below the configured threshold must include explicit caveats
- Do not present low-confidence analysis as high-confidence
- Do not omit the confidence indicator to avoid appearing uncertain

**Violation severity:** MEDIUM -- hidden uncertainty leads to bad decisions.

---

### Constraint 7: Never Cross Project Boundaries Without Authorization

- File operations must stay within the configured `project.root`
- Information from one project must not be referenced in another without explicit instruction
- Shared resources (templates, configs) are the only exception
- If a task requires cross-project access, post a REQUEST and wait for authorization

**Violation severity:** HIGH -- cross-contamination compromises project isolation.

---

### Constraint 8: Never Skip the WDC Panel on Substantive Output

- If `wdc.enabled` is true in config, all substantive outputs must be WDC-certified
- Do not bypass WDC to save time
- Do not self-certify -- all three personas must independently score
- Light review is acceptable where defined, but review cannot be skipped entirely

**Violation severity:** MEDIUM -- uncertified output has no quality guarantee.

---

## 3. Known Traps Table

Domain-specific patterns that commonly lead to guardrail violations. This table is populated per-project.

| Trap ID | Description | Guardrail at Risk | Mitigation |
|---------|-------------|-------------------|------------|
| `[TRAP_001]` | `[DESCRIPTION]` | `[CONSTRAINT_#]` | `[MITIGATION_ACTION]` |
| `[TRAP_002]` | `[DESCRIPTION]` | `[CONSTRAINT_#]` | `[MITIGATION_ACTION]` |
| `[TRAP_003]` | `[DESCRIPTION]` | `[CONSTRAINT_#]` | `[MITIGATION_ACTION]` |

### Adding Traps

When a new trap is identified during project execution:

1. Assign the next sequential TRAP_ID
2. Describe the pattern that leads to the violation
3. Identify which guardrail constraint(s) it threatens
4. Define the specific mitigation action
5. Post a SYNC to Asana so both agents are aware

### Trap Template

```
TRAP_ID:      TRAP_[NNN]
Description:  [What the trap looks like when encountered]
Triggered by: [What input or situation activates this trap]
Guardrail:    Constraint [N] -- [CONSTRAINT_NAME]
Mitigation:   [Specific action to avoid the trap]
Added:        [DATE]
Added by:     [AGENT_LOCAL | AGENT_CLOUD | HUMAN]
```

---

## 4. Exception Protocol

If a guardrail must be overridden:

1. **Human operator** must explicitly authorize the exception
2. The authorization must be **documented** with:
   - Which constraint is being overridden
   - Why the override is necessary
   - What the scope of the override is (one-time vs. ongoing)
   - What compensating controls are in place
3. The exception is logged in the version registry
4. Both agents are notified via Asana ALERT
5. The exception expires at the end of the current task unless explicitly extended

**No agent may self-authorize a guardrail exception. Ever.**

---

## 5. Violation Response

If a guardrail violation is detected (by either agent or by the human operator):

| Severity | Response |
|----------|----------|
| CRITICAL | Halt all processing, post ALERT, await human instruction |
| HIGH | Flag the violation, continue other tasks, post ALERT |
| MEDIUM | Log the violation, add to next status report, self-correct |

All violations are logged in the version registry under `guardrail_violations`:

```json
{
  "violation_id": "V_[NNN]",
  "timestamp": "[ISO_TIMESTAMP]",
  "constraint": "[CONSTRAINT_NUMBER]",
  "severity": "[CRITICAL | HIGH | MEDIUM]",
  "description": "[WHAT_HAPPENED]",
  "detected_by": "[AGENT_LOCAL | AGENT_CLOUD | HUMAN]",
  "resolution": "[HOW_IT_WAS_RESOLVED]"
}
```

---

*Guardrails are absolute. They exist to protect the integrity of the pipeline and the work product. Adherence is mandatory.*
