# Ciphergy — Medical Case Management Example
## Complex Patient Care Coordination

### Domain Configuration

```yaml
# config/domains/medical.yaml
domain:
  name: "medical"
  display: "Medical Case Management"

wdc:
  agent_1_name: "Attending Physician"
  agent_1_directive: "Does this treatment plan address the primary diagnosis?"
  agent_2_name: "Clinical Review (Adversarial)"
  agent_2_directive: "What are the contraindications? What could go wrong? What did we miss?"
  agent_3_name: "Insurance / Compliance"
  agent_3_directive: "Is this covered? Does it meet standard of care? Documentation sufficient?"

input_gates:
  tone_register: "clinical"
  scope_isolation:
    - "patient_data_is_HIPAA_protected"
    - "separate_patients_cannot_cross"

confidence:
  categories:
    - name: "diagnosis"
      description: "Diagnostic confidence"
      elements: ["symptoms_documented", "labs_confirmed", "imaging_reviewed", "differential_ruled_out", "specialist_consulted"]
    - name: "treatment"
      description: "Treatment plan confidence"
      elements: ["evidence_based", "contraindications_checked", "patient_consent", "insurance_approved", "monitoring_plan"]
  threshold: 85  # Higher bar for medical decisions

known_traps:
  - trap: "Lab result without reference range context"
    rule: "Always include normal range alongside result"
  - trap: "Medication interaction not checked"
    rule: "Run interaction check against full med list before recommending"
  - trap: "Copying findings between patients"
    rule: "NEVER — each patient file is isolated"

monitored_files:
  - pattern: "PATIENT_SUMMARY*.md"
    category: "clinical"
  - pattern: "TREATMENT_PLAN*.md"
    category: "clinical"
  - pattern: "_RED_ALERTS.md"
    category: "operational"
  - pattern: "LAB_TRACKER*.md"
    category: "monitoring"
```

### Cascade Triggers (Medical)

| Trigger | Example | Cascade |
|---------|---------|---------|
| `new-evidence` | New lab result received | Score → check against thresholds → RED ALERT if critical value |
| `answered` | Patient reports new symptom | Update differential → re-score diagnosis confidence |
| `phase-change` | Patient admitted / discharged / transferred | Update care plan, medication reconciliation |
| `critical-value` | Lab result outside normal range | IMMEDIATE RED ALERT → attending notification |

### HIPAA Note

All patient data processed through Ciphergy must comply with HIPAA requirements. The local agent processes PHI on a HIPAA-compliant local machine. The cloud agent should NOT receive PHI in project knowledge — only de-identified summaries. The sync pipeline must be configured to exclude PHI-containing files from the monitored list.
