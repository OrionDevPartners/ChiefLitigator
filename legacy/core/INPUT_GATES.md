# INPUT GATES -- 7-Gate Input Filtering Pipeline

> **Ciphergy Pipeline v1.0**
> Purpose: Classify, verify, and filter all incoming information before processing
> Applies to: Both AGENT LOCAL and AGENT CLOUD

---

## 1. Overview

Every piece of incoming information -- whether from the human operator, from the other agent, from a file, or from an external source -- must pass through all 7 gates before being acted upon. Gates are evaluated in sequence. A failure at any gate triggers a defined response (not necessarily rejection).

---

## 2. The 7 Gates

### Gate 1: CLASSIFY

**Question:** *What type of input is this?*

Classify the input into one or more categories:

| Classification | Definition | Example |
|---------------|------------|---------|
| **FACT** | Verifiable statement with a truth value | "The deadline is March 15" |
| **ASSERTION** | Claim presented as true but not yet verified | "The opposing position is weak" |
| **INSTRUCTION** | Directive to take a specific action | "Draft a response to this" |
| **EMOTION** | Expression of feeling, frustration, urgency | "This is unacceptable" |
| **MIXED** | Contains multiple types | "The deadline is March 15 and this is unacceptable -- draft a response" |

**On MIXED:** Decompose into individual components and classify each separately.

**On EMOTION:** Acknowledge but do not let emotional framing alter factual analysis. Emotional urgency does not change confidence scores.

---

### Gate 2: EVIDENCE

**Question:** *What supports this?*

For every FACT or ASSERTION, identify the supporting evidence:

| Evidence Level | Definition | Action |
|---------------|------------|--------|
| **DOCUMENTED** | Supported by a file, record, or verifiable source | Proceed with high confidence |
| **REFERENCED** | Source is cited but not yet verified | Verify before relying upon |
| **CLAIMED** | Stated without citation | Flag for verification |
| **ASSUMED** | Implied or inferred, not explicitly stated | Flag and confirm with operator |
| **NONE** | No supporting evidence whatsoever | Do not treat as fact |

Log the evidence level for each factual component.

---

### Gate 3: VERIFICATION

**Question:** *Are claims verified?*

For inputs classified as FACT or ASSERTION with evidence level below DOCUMENTED:

1. **Cross-reference** against known project files and version registry
2. **Search** persistent memory (AGENT CLOUD) or local files (AGENT LOCAL)
3. **Flag contradictions** -- if the claim conflicts with known information, post ALERT

Verification outcomes:

| Outcome | Action |
|---------|--------|
| **VERIFIED** | Proceed normally |
| **UNVERIFIED** | Note as unverified, include caveat in any output that relies on it |
| **CONTRADICTED** | Post ALERT, do not rely on the claim without resolution |
| **UNVERIFIABLE** | Note as unverifiable, include caveat, request human confirmation |

---

### Gate 4: TONE

**Question:** *Does this match the required register?*

Evaluate whether the input's tone is appropriate for the context:

| Register | When Used | Characteristics |
|----------|-----------|-----------------|
| **FORMAL** | External communications, filings, submissions | Precise, neutral, professional |
| **ANALYTICAL** | Internal analysis, strategy documents | Clear, structured, evidence-based |
| **OPERATIONAL** | Agent-to-agent communication, status updates | Concise, direct, action-oriented |
| **CONVERSATIONAL** | Human-to-agent discussion | Natural, responsive, adaptive |

If the input's tone does not match the required register for the current task:
- For outputs: Adjust tone before delivery
- For inputs: Process the content regardless of tone, but note the mismatch

---

### Gate 5: SCOPE

**Question:** *Does this cross-contaminate projects?*

Verify that the input belongs to the current project context:

1. **Check project boundary** -- does this reference files, entities, or contexts from a different project?
2. **Check information isolation** -- would acting on this leak information between projects?
3. **Check resource boundaries** -- would this modify files outside the project root?

| Scope Result | Action |
|-------------|--------|
| **IN SCOPE** | Proceed normally |
| **ADJACENT** | Proceed with caution, note the cross-reference |
| **OUT OF SCOPE** | Do not process, notify operator |
| **CONTAMINATION RISK** | STOP, post ALERT, await human instruction |

---

### Gate 6: CONFIDENCE

**Question:** *What is the confidence level?*

Assign a confidence score (0-100) based on the cumulative gate results:

| Factor | Impact on Confidence |
|--------|---------------------|
| All facts DOCUMENTED and VERIFIED | +30 |
| All facts REFERENCED and VERIFIED | +20 |
| Some facts UNVERIFIED | -10 per unverified fact |
| Any fact CONTRADICTED | -25 per contradiction |
| Tone matches register | +5 |
| In scope | +10 |
| Evidence level NONE on any component | -15 per component |

**Threshold:** If confidence falls below `alerts.confidence_threshold` (from config), the input is flagged and the output must include a confidence warning.

---

### Gate 7: SYNC

**Question:** *Does this affect monitored files?*

Check whether the input implies changes to any file in the `sync.monitored_files` list:

1. **Scan for file references** -- does the input mention specific files?
2. **Check monitored list** -- are any referenced files in the monitored set?
3. **Check cascade triggers** -- would acting on this input trigger a cascade?

| Sync Result | Action |
|------------|--------|
| **NO SYNC NEEDED** | Proceed normally |
| **SYNC TRIGGERED** | Execute cascade per AGENT_LOCAL protocol |
| **MONITORED FILE AFFECTED** | Update hash, post SYNC to Asana, update registry |
| **CONFLICT DETECTED** | STOP, post ALERT, await resolution |

---

## 3. Gate Summary Log

After all 7 gates, produce an internal log entry:

```
--- INPUT GATE LOG ---
Timestamp:      [ISO_TIMESTAMP]
Input Source:    [HUMAN | AGENT_LOCAL | AGENT_CLOUD | FILE | EXTERNAL]
Classification: [FACT | ASSERTION | INSTRUCTION | EMOTION | MIXED]
Evidence Level: [DOCUMENTED | REFERENCED | CLAIMED | ASSUMED | NONE]
Verification:   [VERIFIED | UNVERIFIED | CONTRADICTED | UNVERIFIABLE]
Tone Match:     [YES | NO -- expected: REGISTER]
Scope:          [IN SCOPE | ADJACENT | OUT OF SCOPE | CONTAMINATION RISK]
Confidence:     [XX]%
Sync Impact:    [NONE | TRIGGERED | CONFLICT]
--- END GATE LOG ---
```

This log is retained internally for the duration of the session. It is not posted to Asana unless an ALERT is triggered.

---

## 4. Gate Failure Responses

| Gate | Failure Condition | Response |
|------|------------------|----------|
| CLASSIFY | Cannot determine type | Ask operator for clarification |
| EVIDENCE | No evidence for a critical claim | Flag, reduce confidence, caveat output |
| VERIFICATION | Contradiction found | Post ALERT, halt processing of that claim |
| TONE | Severe mismatch | Adjust output tone, note adjustment |
| SCOPE | Cross-contamination risk | STOP, post ALERT |
| CONFIDENCE | Below threshold | Include confidence warning in all output |
| SYNC | Conflict detected | STOP, post ALERT, await resolution |

---

*All inputs are filtered. No exceptions. Gates run automatically on every substantive input.*
