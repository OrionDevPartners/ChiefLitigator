# Ciphergy — Startup Due Diligence Example
## Investment Analysis & Deal Execution

### Domain Configuration

```yaml
# config/domains/startup-diligence.yaml
domain:
  name: "startup-diligence"
  display: "Startup Due Diligence"

wdc:
  agent_1_name: "Deal Lead"
  agent_1_directive: "Does this finding support or undermine the investment thesis?"
  agent_2_name: "Risk Committee"
  agent_2_directive: "What's the downside? What are they hiding? What breaks the deal?"
  agent_3_name: "LP Perspective"
  agent_3_directive: "Would our LPs be comfortable with this? Does it meet fund mandates?"

input_gates:
  tone_register: "professional"
  scope_isolation:
    - "target_company_data_room_is_confidential"
    - "competing_deals_cannot_cross"

confidence:
  categories:
    - name: "thesis_pillar"
      description: "Investment thesis supporting element"
      elements: ["market_size_validated", "revenue_verified", "team_assessed", "tech_differentiated", "unit_economics_confirmed"]
    - name: "risk_factor"
      description: "Identified deal risk"
      elements: ["severity", "probability", "mitigability", "discovery_completeness"]
  threshold: 80  # Higher bar for investment decisions

known_traps:
  - trap: "Unaudited financials treated as fact"
    rule: "Always flag: [UNAUDITED — VERIFY WITH INDEPENDENT AUDIT]"
  - trap: "Founder verbal claims without documentation"
    rule: "Nothing in the memo without a document reference"
  - trap: "Market size from pitch deck without independent validation"
    rule: "Cross-reference with Pitchbook, CB Insights, or primary research"

monitored_files:
  - pattern: "INVESTMENT_MEMO*.md"
    category: "deliverables"
  - pattern: "RISK_MATRIX*.md"
    category: "operational"
  - pattern: "_RED_ALERTS.md"
    category: "operational"
  - pattern: "FINANCIAL_MODEL*.xlsx"
    category: "analysis"
```

### Cascade Triggers (Due Diligence)

| Trigger | Example | Cascade |
|---------|---------|---------|
| `new-evidence` | New financial document received from data room | Score → update risk matrix → update memo |
| `answered` | Founder clarifies customer concentration | Propagate to revenue analysis + risk matrix |
| `phase-change` | Term sheet signed, moving to confirmatory DD | Update timeline, expand document request list |
| `red-flag` | Material undisclosed liability found | RED ALERT → immediate escalation to deal lead |
