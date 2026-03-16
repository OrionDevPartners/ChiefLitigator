# Confidence Monitor -- [PROJECT_NAME]

> **Domain:** [DOMAIN]
> **Last Updated:** [YYYY-MM-DD]
> **Threshold:** [CONFIDENCE_THRESHOLD]%

---

## Section 1: Active Claims

Claims currently above the confidence threshold and relied upon in active work product.

| # | Claim | Confidence | Evidence Level | Last Verified | Source | Notes |
|---|-------|-----------|---------------|--------------|--------|-------|
| 1 | [CLAIM_TEXT] | [XX]% | [DOCUMENTED/REFERENCED/CLAIMED] | [DATE] | [SOURCE_REF] | [NOTES] |
| 2 | [CLAIM_TEXT] | [XX]% | [DOCUMENTED/REFERENCED/CLAIMED] | [DATE] | [SOURCE_REF] | [NOTES] |
| 3 | [CLAIM_TEXT] | [XX]% | [DOCUMENTED/REFERENCED/CLAIMED] | [DATE] | [SOURCE_REF] | [NOTES] |

---

## Section 2: Building Claims

Claims currently **below** the confidence threshold. These cannot be relied upon in substantive output without caveats.

| # | Claim | Confidence | Gap | Action Needed | Deadline | Owner |
|---|-------|-----------|-----|--------------|----------|-------|
| 1 | [CLAIM_TEXT] | [XX]% | [WHAT_IS_MISSING] | [ACTION] | [DATE] | [AGENT/HUMAN] |
| 2 | [CLAIM_TEXT] | [XX]% | [WHAT_IS_MISSING] | [ACTION] | [DATE] | [AGENT/HUMAN] |
| 3 | [CLAIM_TEXT] | [XX]% | [WHAT_IS_MISSING] | [ACTION] | [DATE] | [AGENT/HUMAN] |

---

## Section 3: Collection Tracker

Status of evidence and supporting materials across all claims.

### In Hand

Evidence that has been obtained and verified.

| # | Item | File/Location | Obtained | Verified By |
|---|------|--------------|----------|-------------|
| 1 | [ITEM_DESCRIPTION] | [FILE_PATH] | [DATE] | [AGENT/HUMAN] |

### Obtainable

Evidence that is known to exist and can be acquired.

| # | Item | Source | Estimated Availability | Action Required |
|---|------|--------|----------------------|-----------------|
| 1 | [ITEM_DESCRIPTION] | [SOURCE] | [DATE/TIMEFRAME] | [ACTION] |

### Dependent

Evidence that depends on external parties or events.

| # | Item | Depends On | Expected By | Fallback Plan |
|---|------|-----------|-------------|---------------|
| 1 | [ITEM_DESCRIPTION] | [DEPENDENCY] | [DATE] | [FALLBACK] |

---

## Section 4: Threshold Alerts

Automated alerts triggered when confidence drops below [CONFIDENCE_THRESHOLD]%.

| Alert # | Date | Claim | Previous Confidence | Current Confidence | Trigger | Action Taken |
|---------|------|-------|--------------------|--------------------|---------|-------------|
| [N] | [DATE] | [CLAIM_REF] | [OLD]% | [NEW]% | [WHAT_CHANGED] | [ACTION] |

---

## Change Log

| Date | Change | Changed By |
|------|--------|-----------|
| [DATE] | [DESCRIPTION] | [AGENT/HUMAN] |

---

*This monitor is maintained by AGENT LOCAL and reviewed by AGENT CLOUD. Human confirmation is required for all confidence score changes on Active Claims.*
