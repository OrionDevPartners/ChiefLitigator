# WDC PANEL -- Weighted Debate Consensus Protocol

> **Ciphergy Pipeline v1.0**
> Purpose: Multi-persona review for quality assurance on all substantive outputs
> Applies to: Both AGENT LOCAL and AGENT CLOUD

---

## 1. Overview

The Weighted Debate Consensus (WDC) Panel is a structured internal review process. Every substantive output passes through three personas, each evaluating from a distinct perspective. The final score determines whether the output is certified for delivery.

This is not optional. It is a hard requirement for all outputs classified as substantive.

---

## 2. The Three Personas

### Agent 1: The Strategist (Weight: 40%)

**Question:** *Does this advance the objective?*

Evaluates:
- Alignment with stated project goals
- Whether the output moves the project forward or is tangential
- Opportunity cost -- is this the highest-value action right now?
- Coherence with the broader strategy
- Whether timing is appropriate

Scoring:
- **10** -- Directly advances the primary objective with optimal timing
- **7-9** -- Advances the objective with minor reservations
- **4-6** -- Partially relevant but not the highest priority
- **1-3** -- Tangential or poorly timed
- **0** -- Counterproductive to the objective

---

### Agent 2: The Red Team (Weight: 35%)

**Question:** *How would an adversary exploit this?*

Evaluates:
- Factual vulnerabilities -- are there claims that can be challenged?
- Logical weaknesses -- are there gaps in reasoning?
- Procedural exposure -- does this violate any rules or protocols?
- Information leakage -- does this reveal more than intended?
- Attack surface -- what is the worst-case interpretation?

Scoring:
- **10** -- No exploitable vulnerabilities found
- **7-9** -- Minor vulnerabilities, unlikely to be exploited
- **4-6** -- Moderate vulnerabilities that should be addressed
- **1-3** -- Significant vulnerabilities that must be fixed before delivery
- **0** -- Critical vulnerability, output must be rejected

---

### Agent 3: The Evaluator (Weight: 25%)

**Question:** *Is this procedurally sound?*

Evaluates:
- Format compliance -- does it match required formatting?
- Completeness -- are all required elements present?
- Accuracy -- are dates, names, references correct?
- Tone -- does it match the required register for the audience?
- Internal consistency -- does it contradict itself?

Scoring:
- **10** -- Procedurally flawless
- **7-9** -- Minor procedural issues, easily corrected
- **4-6** -- Notable procedural gaps that need attention
- **1-3** -- Significant procedural failures
- **0** -- Fundamentally non-compliant

---

## 3. Scoring & Certification

### Weighted Score Calculation

```
FINAL_SCORE = (Strategist_Score * 0.40) + (Red_Team_Score * 0.35) + (Evaluator_Score * 0.25)
```

### Certification Thresholds

| Score Range | Result | Action |
|-------------|--------|--------|
| 8.0 -- 10.0 | CERTIFIED | Output approved for delivery |
| 6.0 -- 7.9 | CONDITIONAL | Output approved with noted caveats |
| 4.0 -- 5.9 | REVISION REQUIRED | Must address flagged issues before delivery |
| 0.0 -- 3.9 | REJECTED | Output must be substantially reworked |

---

## 4. Certification Block Format

Every certified output must include this block at the end:

```
============================================
WDC CERTIFICATION
--------------------------------------------
Project:    [PROJECT_NAME]
Output:     [DOCUMENT_TITLE_OR_DESCRIPTION]
Date:       [YYYY-MM-DD]
Review:     [FULL | LIGHT]
--------------------------------------------
Strategist: [SCORE]/10 -- [ONE_LINE_RATIONALE]
Red Team:   [SCORE]/10 -- [ONE_LINE_RATIONALE]
Evaluator:  [SCORE]/10 -- [ONE_LINE_RATIONALE]
--------------------------------------------
Weighted Score: [FINAL_SCORE]/10.0
Result:     [CERTIFIED | CONDITIONAL | REVISION REQUIRED | REJECTED]
Caveats:    [LIST OR "None"]
============================================
```

---

## 5. Full Review vs. Light Review

Not all outputs require the same depth of analysis.

### Full Review Triggers

A full review is required when:

- The output will be submitted to an external party
- The output contains factual claims that will be relied upon
- The output involves financial, strategic, or high-stakes decisions
- The output will become part of the permanent record
- AGENT CLOUD or AGENT LOCAL flags the output as high-risk
- The output crosses project or domain boundaries

Full review: Each persona provides detailed rationale (2-3 sentences minimum).

### Light Review Triggers

A light review is sufficient when:

- The output is an internal working document
- The output is a routine status update or progress report
- The output is a draft that will undergo further revision
- The output is a response to a straightforward factual question
- The confidence level is above 90% and no red flags are present

Light review: Each persona provides a score and one-line rationale only.

---

## 6. Dispute Resolution

If any single persona scores below 4.0, the output is **automatically flagged** regardless of the weighted total. The following escalation applies:

| Condition | Action |
|-----------|--------|
| Strategist < 4.0 | Re-evaluate objective alignment before proceeding |
| Red Team < 4.0 | Mandatory vulnerability remediation before delivery |
| Evaluator < 4.0 | Mandatory procedural correction before delivery |
| Two personas < 4.0 | Output rejected, full rework required |
| All three < 4.0 | Output rejected, escalate to human for direction |

---

## 7. Domain-Agnostic Application

The WDC Panel adapts to any domain through configuration:

| Config Value | Effect |
|-------------|--------|
| `wdc.strategist_weight` | Adjusts Strategist influence (default: 0.40) |
| `wdc.red_team_weight` | Adjusts Red Team influence (default: 0.35) |
| `wdc.evaluator_weight` | Adjusts Evaluator influence (default: 0.25) |
| `wdc.enabled` | Master toggle (default: true) |

Weights must always sum to 1.00.

The Strategist evaluates against `[PROJECT_NAME]` objectives.
The Red Team evaluates against `[DOMAIN]`-specific adversarial patterns.
The Evaluator evaluates against `[DOMAIN]`-specific procedural requirements.

---

## 8. Logging

All WDC reviews are logged in the version registry under the `wdc_reviews` array:

```json
{
  "file": "[RELATIVE_PATH]",
  "review_date": "[ISO_TIMESTAMP]",
  "review_type": "FULL | LIGHT",
  "strategist_score": 0.0,
  "red_team_score": 0.0,
  "evaluator_score": 0.0,
  "weighted_score": 0.0,
  "result": "CERTIFIED | CONDITIONAL | REVISION REQUIRED | REJECTED",
  "caveats": []
}
```

---

*The WDC Panel is mandatory for all substantive outputs. No exceptions without explicit human override.*
