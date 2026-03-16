# RED ALERTS -- [PROJECT_NAME]

> **Domain:** [DOMAIN]
> **Last Updated:** [YYYY-MM-DD]
> **Confidence Threshold:** [CONFIDENCE_THRESHOLD]%
> **Active Alerts:** [COUNT]

---

## Active Alerts

Items requiring immediate attention. Do not clear without human confirmation.

| Alert # | Date | Claim / Element | Confidence | Trigger | Required Action | Status |
|---------|------|-----------------|-----------|---------|-----------------|--------|
| A-[NNN] | [DATE] | [CLAIM_OR_ELEMENT] | [XX]% | [WHAT_TRIGGERED_ALERT] | [ACTION_REQUIRED] | OPEN |
| A-[NNN] | [DATE] | [CLAIM_OR_ELEMENT] | [XX]% | [WHAT_TRIGGERED_ALERT] | [ACTION_REQUIRED] | OPEN |
| A-[NNN] | [DATE] | [CLAIM_OR_ELEMENT] | [XX]% | [WHAT_TRIGGERED_ALERT] | [ACTION_REQUIRED] | OPEN |

### Alert Detail

For each active alert, expand details here:

#### A-[NNN]: [SHORT_TITLE]

- **Date Opened:** [DATE]
- **Opened By:** [AGENT_LOCAL / AGENT_CLOUD / HUMAN]
- **Claim:** [FULL_CLAIM_TEXT]
- **Current Confidence:** [XX]%
- **Threshold:** [CONFIDENCE_THRESHOLD]%
- **Trigger Event:** [DETAILED_DESCRIPTION_OF_WHAT_TRIGGERED_THIS]
- **Affected Files:** [LIST_OF_FILE_PATHS]
- **Required Action:** [SPECIFIC_ACTION_NEEDED]
- **Assigned To:** [AGENT_LOCAL / AGENT_CLOUD / HUMAN]
- **Deadline:** [DATE_OR_ASAP]
- **Status:** OPEN

---

## Below-Threshold Tracking

Claims that are approaching the confidence threshold from above. Early warning system.

| # | Claim | Current Confidence | Threshold Distance | Trend | Watch Since |
|---|-------|-------------------|--------------------|-------|-------------|
| 1 | [CLAIM_TEXT] | [XX]% | [X]% above | [RISING/STABLE/FALLING] | [DATE] |
| 2 | [CLAIM_TEXT] | [XX]% | [X]% above | [RISING/STABLE/FALLING] | [DATE] |

---

## Confirmed / Resolved

Alerts that have been addressed and confirmed by the human operator.

| Alert # | Date Opened | Date Resolved | Resolution | Confirmed By |
|---------|------------|---------------|------------|-------------|
| A-[NNN] | [DATE] | [DATE] | [HOW_RESOLVED] | [HUMAN_NAME] |

---

## Instructions

### For Agents

1. **Opening an alert:** Assign the next sequential alert number (A-001, A-002, etc.)
2. **Populating details:** Fill in all fields in the Alert Detail section
3. **Asana notification:** Post an ALERT message to Asana with the alert number and summary
4. **Do not resolve alerts.** Only the human operator may move an alert to Confirmed/Resolved

### For the Human Operator

1. **Review active alerts** at the start of each work session
2. **To resolve:** Move the alert row from Active to Confirmed, fill in resolution details
3. **To escalate:** Change the Required Action and re-assign
4. **Below-threshold items** do not require action unless they cross the threshold

### Alert Numbering

- Format: `A-NNN` (e.g., A-001, A-002)
- Numbers are sequential and never reused
- Resolved alerts retain their number in the Confirmed section

---

*Alerts are never deleted. They are either OPEN or RESOLVED. The human operator is the sole authority on resolution.*
