# Ciphergy — Legal Domain Example
## Pro Se / Litigation Case Management

### Domain Configuration

```yaml
# config/domains/legal.yaml
domain:
  name: "legal"
  display: "Litigation Case Management"

wdc:
  agent_1_name: "Senior Litigation Strategist"
  agent_1_directive: "Does this advance the client's litigation posture?"
  agent_2_name: "Opposing Counsel (Red Team)"
  agent_2_directive: "How would defense counsel attack this? What motion does this enable?"
  agent_3_name: "The Bench (Judge)"
  agent_3_directive: "Is this procedurally sound? Would this survive a motion to dismiss?"

input_gates:
  tone_register: "glacier"  # cold, clinical, no emotions
  scope_isolation:
    - "separate_matters_cannot_cross"
    - "settlement_comms_protected_90.408"

confidence:
  categories:
    - name: "count"
      description: "Legal count/cause of action"
      elements: ["statutory_basis", "factual_support", "evidence_in_hand", "witness_available", "survives_mtd"]
    - name: "conspiracy"
      description: "Potential co-conspirator"
      elements: ["temporal_proximity", "behavioral_anomaly", "nexus_connection"]
  threshold: 75

known_traps:
  - trap: "Punitive damages in initial complaint"
    rule: "Section 768.72 prohibits — always purge from Phase 1"
  - trap: "Fabricated case citations"
    rule: "NEVER — use [CASE LAW NEEDED — VERIFY] if unsure"
  - trap: "Settlement communications in filings"
    rule: "Section 90.408 protected — never reference in court documents"

monitored_files:
  # v-numbered filings
  - pattern: "v*_*.docx"
    category: "filings"
  # Strategy docs
  - pattern: "*Strategy*.md"
    category: "strategy"
  # Evidence monitors
  - pattern: "EVIDENCE_CONFIDENCE_MONITOR.md"
    category: "operational"
  - pattern: "_RED_ALERTS.md"
    category: "operational"
```

### What Agent Local Does (Legal)

- Reads/organizes case folder (evidence, filings, correspondence)
- Generates litigation analysis documents (damages tables, case law indices)
- Monitors evidence confidence per count
- Manages version control on locked court filings (v19 → v20 protocol)
- Scores potential co-conspirators on temporal/behavioral/nexus axes
- Drafts subpoenas, interrogatories, document requests

### What Agent Cloud Does (Legal)

- Maintains case narrative across sessions
- Drafts communications (to court, to opposing counsel)
- Stress-tests filings through WDC panel (Strategist / Red Team / Bench)
- Researches case law via web search
- Remembers prior strategic decisions via system memory

### Cascade Triggers (Legal)

| Trigger | Example | Cascade |
|---------|---------|---------|
| `new-evidence` | New witness statement obtained | Score → threshold check → alert → update context |
| `answered` | Client confirms signed contract existed | Propagate to tortious interference analysis |
| `phase-change` | Complaint filed, case number assigned | Update all Phase 2 documents with case number |
| `case-law-verified` | Westlaw confirms citation is valid | Update case law index |
| `settlement-event` | Settlement offer received | Log in tracker (protected — never in filings) |
