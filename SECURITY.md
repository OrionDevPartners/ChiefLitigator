# Security Policy

**Project:** Cyphergy -- AI-Powered Legal Document Analysis & Motion Drafting
**Maintainer:** Bo Pennington (bo@symio.ai)
**Organization:** Analog AGI / OrionDevPartners

---

## Supported Versions

| Version | Supported | Notes |
|---------|-----------|-------|
| 0.x.x (current) | Yes | Active development, security patches applied immediately |
| Pre-release | No | Not intended for production use |

Security patches are applied to the latest release only. Older versions
are not backported unless a critical vulnerability affects deployed instances.

---

## Reporting a Vulnerability

**DO NOT** open a public GitHub issue for security vulnerabilities.

### Responsible Disclosure Process

1. **Email:** Send a detailed report to **bo@symio.ai** with subject line
   `[SECURITY] Cyphergy - Brief Description`.

2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if applicable)
   - Your preferred attribution (or anonymous)

3. **Response Timeline:**
   - **Acknowledgment:** Within 24 hours
   - **Initial Assessment:** Within 72 hours
   - **Fix Target:** Within 7 days for critical, 30 days for medium/low
   - **Disclosure:** Coordinated with reporter after fix is deployed

4. **What to Expect:**
   - We will confirm receipt and provide a tracking identifier.
   - We will keep you informed of our progress.
   - We will credit you in the advisory (unless you prefer anonymity).
   - We will not pursue legal action against good-faith security researchers.

### Scope

In scope:
- Authentication and authorization bypass
- Data exposure (case files, PII, legal documents)
- Injection attacks (SQL, XSS, command injection)
- Rate limiting bypass
- LLM prompt injection affecting legal outputs
- Citation integrity attacks (manipulating legal citations)
- Secrets exposure in logs, error messages, or API responses

Out of scope:
- Social engineering of team members
- Physical attacks
- Denial of service via volumetric attacks (handled by Cloudflare)
- Vulnerabilities in third-party services (report to them directly)

---

## Security Architecture

### Data Classification

Cyphergy processes 4 tiers of data sensitivity:

| Tier | Classification | Examples | Controls |
|------|---------------|----------|----------|
| T1 | **Public** | Marketing content, public court records | Standard HTTPS |
| T2 | **Internal** | System logs, aggregated analytics | Access control, log masking |
| T3 | **Confidential** | Case strategies, draft motions, client communications | AES-256 encryption, per-tenant isolation |
| T4 | **Restricted** | PHI (medical malpractice), financial records, PII | HIPAA/GDPR controls, cryptographic deletion, audit logging |

### Authentication & Authorization

- API authentication via bearer tokens (JWT or API keys)
- Per-tenant data isolation (no cross-tenant data access)
- Role-based access control (RBAC) for firm-level permissions
- All authentication events logged for audit trail

### Rate Limiting

4-layer defense (see `src/security/rate_limiter.py`):
1. Per-IP: Prevents brute force and scraping
2. Per-User: Limits individual account abuse
3. Per-Tenant: Aggregate cap per organization
4. Global Circuit Breaker: Protects downstream services

### Network Security

- Cloudflare WAF with custom rules for legal API protection
- HSTS with preload for all connections
- TLS 1.3 minimum (configured at load balancer)
- Geographic restrictions available (US-only by default)

### LLM Security

- All-Opus model selection (no cost-optimized models for legal analysis)
- Citation Verification Chain with external retrieval requirement
- Multi-agent consensus (WDC) prevents single-model hallucination
- Prompt injection detection in user inputs
- LLM outputs are validated, never trusted directly

---

## Known Security Considerations

### Legal Data Handling
- **Case files contain privileged attorney-client information.** All case data
  is treated as T3/T4 (Confidential/Restricted) by default.
- **Court filings are time-sensitive.** Integrity attacks that alter filing
  deadlines could cause missed court dates with severe legal consequences.
- **Citation accuracy is non-negotiable.** Fabricated legal citations
  (hallucinations) can result in court sanctions and malpractice liability.

### PII and Protected Data
- Medical malpractice cases contain Protected Health Information (PHI)
  regulated by HIPAA (45 CFR Parts 160, 164).
- Client contact information falls under GDPR (EU clients) and
  CCPA (California clients).
- PII scrubbing is applied at 5 stages in the processing pipeline.

### LLM Provider Data
- Case data sent to LLM providers (Anthropic) for analysis.
- Anthropic's data handling policy: inputs/outputs are not used for training.
- No case data is cached by the LLM provider beyond the request lifecycle.
- Provider selection is CPAA-configurable (can switch providers if policy changes).

### Secrets Management
- All secrets are environment variables (never in code or config files).
- Secret masking filter applied to all log output.
- Health check endpoint reports configured vs. missing integrations
  without exposing actual values.

---

## Security Checklist for Contributors

Before submitting a pull request, verify:

### Code
- [ ] No secrets, API keys, or passwords in code (check with `git diff --cached`)
- [ ] No hardcoded URLs, IPs, or hostnames (use environment variables)
- [ ] Input validation on all user-facing endpoints
- [ ] SQL queries use parameterized statements (never string concatenation)
- [ ] Error messages do not expose internal details (stack traces, file paths)
- [ ] Log messages do not contain PII, secrets, or case data

### Authentication & Authorization
- [ ] New endpoints require authentication (no accidental public endpoints)
- [ ] Authorization checks verify tenant isolation (user can only access own data)
- [ ] Admin endpoints require elevated permissions

### Data Handling
- [ ] New data fields classified per the 4-tier model
- [ ] T3/T4 data encrypted at rest and in transit
- [ ] PII fields identified and included in scrubbing pipeline
- [ ] Deletion requests trigger cryptographic deletion (not just soft delete)

### Dependencies
- [ ] New dependencies reviewed for known vulnerabilities (`pip audit`)
- [ ] Dependencies pinned to specific versions (no wildcards)
- [ ] No unnecessary dependencies added

### Testing
- [ ] Security-relevant changes have adversarial test cases
- [ ] Rate limiting changes tested under load
- [ ] Authentication changes tested for bypass scenarios

---

## Incident Response

1. **Detection:** Automated monitoring (Sentry, Cloudflare alerts, audit logs)
2. **Containment:** Immediate API key rotation, affected tenant isolation
3. **Investigation:** Audit trail via request IDs, structured logging
4. **Recovery:** Data integrity verification, affected user notification
5. **Post-mortem:** Root cause analysis added to ERROR_MUSEUM (@M:020)

---

## Compliance References

| Regulation | Applicability | Key Requirements |
|-----------|--------------|-----------------|
| HIPAA (45 CFR 164) | Medical malpractice cases | PHI encryption, access logging, BAA with processors |
| GDPR (EU 2016/679) | EU client data | Data minimization, right to erasure, DPA with processors |
| CCPA (Cal. Civ. Code 1798) | California client data | Disclosure rights, opt-out, deletion on request |
| SOC 2 Type II | All operations | Security, availability, confidentiality controls |

---

*Last Updated: 2026-03-15*
