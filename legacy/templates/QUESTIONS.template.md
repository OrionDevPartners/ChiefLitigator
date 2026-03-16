# Running Questions -- [PROJECT_NAME]

> **Domain:** [DOMAIN]
> **Last Updated:** [YYYY-MM-DD]
> **Open Questions:** [COUNT]

---

## Critical Priority

Questions that block substantive work. Must be answered before proceeding.

| # | Question | Context | Deadline | Asked By | Status |
|---|----------|---------|----------|----------|--------|
| Q-[NNN] | [QUESTION_TEXT] | [WHY_THIS_MATTERS] | [DATE] | [AGENT/HUMAN] | OPEN |

---

## High Priority

Questions that affect quality or accuracy of current work product.

| # | Question | Context | Deadline | Asked By | Status |
|---|----------|---------|----------|----------|--------|
| Q-[NNN] | [QUESTION_TEXT] | [WHY_THIS_MATTERS] | [DATE] | [AGENT/HUMAN] | OPEN |

---

## Medium Priority

Questions that would improve completeness but do not block progress.

| # | Question | Context | Deadline | Asked By | Status |
|---|----------|---------|----------|----------|--------|
| Q-[NNN] | [QUESTION_TEXT] | [WHY_THIS_MATTERS] | [DATE] | [AGENT/HUMAN] | OPEN |

---

## Low Priority

Background questions, clarifications, or future planning items.

| # | Question | Context | Deadline | Asked By | Status |
|---|----------|---------|----------|----------|--------|
| Q-[NNN] | [QUESTION_TEXT] | [WHY_THIS_MATTERS] | [DATE] | [AGENT/HUMAN] | OPEN |

---

## Answered

Questions that have been resolved. Kept for reference and audit trail.

| # | Question | Answer | Answered By | Date Answered | Propagated To |
|---|----------|--------|-------------|--------------|---------------|
| Q-[NNN] | [QUESTION_TEXT] | [ANSWER_TEXT] | [HUMAN/AGENT] | [DATE] | [LIST_OF_FILES_UPDATED] |

---

## Propagation Instructions

When a question is answered, the answer must be propagated to all affected documents:

1. **Move the question** from its priority section to the Answered section
2. **Fill in all fields** in the Answered row, including the answer text
3. **Identify affected files** -- which documents relied on the unknown answer?
4. **Update those files** with the now-known information
5. **Log the propagation** in the "Propagated To" column with file paths
6. **Update the version registry** for each file modified during propagation
7. **Recalculate confidence** for any claims that depended on this question
8. **Post SYNC to Asana** notifying the other agent of the propagation

### If the Answer Changes a Confidence Score

- Update the Confidence Monitor
- If the new score crosses the threshold (up or down), update RED ALERTS accordingly
- Post an ALERT or resolve an existing alert as appropriate

### If the Answer Contradicts Existing Content

- Do NOT automatically overwrite existing content
- Post an ALERT with both the existing content and the new answer
- Wait for human confirmation before propagating the change

---

## Question Numbering

- Format: `Q-NNN` (e.g., Q-001, Q-002)
- Numbers are sequential and never reused
- Answered questions retain their number in the Answered section
- Questions may be re-opened by moving back to a priority section with status `REOPENED`

---

*Questions are a living document. Both agents may add questions. Only humans may provide authoritative answers to Critical and High priority questions.*
