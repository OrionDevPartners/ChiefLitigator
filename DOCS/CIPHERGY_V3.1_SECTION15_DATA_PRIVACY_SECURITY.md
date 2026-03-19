# CIPHERGY V3.1 — SECTION 15: DATA PRIVACY & SECURITY ARCHITECTURE

## Addition to Product Spec V3
## March 15, 2026

---

## DESIGN PHILOSOPHY

Ciphergy handles the most sensitive data a person can entrust to a platform: their legal case. Case facts, evidence, litigation strategy, financial records, medical records, personal communications — all of it flows through the system. Users who find Ciphergy are already in litigation. They are already exposed. The last thing they need is a data breach turning their legal fight into a privacy disaster.

The security framework follows three principles:
1. **Defense in depth** — no single control failure exposes user data. Every layer assumes the layer above it has been compromised.
2. **Least privilege everywhere** — every service, every agent, every API call gets the minimum access required. Nothing more.
3. **Prove it, don't promise it** — every security claim is backed by auditable controls, not marketing language. SOC 2 Type II is the Phase 8 deliverable that proves it.

---

## 15.1 DATA CLASSIFICATION FRAMEWORK

### A. Four-Tier Classification

Every piece of data in Ciphergy is classified into one of four tiers. The classification determines encryption requirements, access controls, retention policies, and deletion procedures.

| Tier | Label | Description | Encryption | Access | Retention |
|------|-------|-------------|------------|--------|-----------|
| **T1** | PUBLIC | Non-sensitive platform data | TLS in transit | Any authenticated user | Indefinite |
| **T2** | INTERNAL | Platform operational data | TLS + AES-256 at rest | Platform operators only | 1 year |
| **T3** | CONFIDENTIAL | Case metadata, timelines, strategy | TLS + AES-256 at rest + field encryption | Tenant owner + authorized users | 7 years |
| **T4** | RESTRICTED | PII, evidence, financial records, medical records, privileged communications | TLS + AES-256 at rest + per-tenant KMS + field-level encryption | Tenant owner only (explicit grant for others) | 7 years + cryptographic deletion |

### B. Classification Examples (Legal Context)

| Data Type | Tier | Rationale |
|-----------|------|-----------|
| Platform changelog, public pricing | T1 — PUBLIC | No competitive or personal sensitivity |
| Agent performance metrics (aggregated) | T2 — INTERNAL | Operational data, no user PII |
| WDC debate scores, agent run logs | T2 — INTERNAL | System telemetry, anonymized |
| Case timeline, claim matrix | T3 — CONFIDENTIAL | Case strategy — disclosure could harm litigation position |
| Litigation strategy documents | T3 — CONFIDENTIAL | Work product equivalent — adversary access is catastrophic |
| Evidence inventory, uploaded documents | T3 — CONFIDENTIAL | Case materials with potential privilege implications |
| Social Security numbers, dates of birth | T4 — RESTRICTED | PII under CCPA, GDPR, state breach notification laws |
| Financial records (bank statements, tax returns) | T4 — RESTRICTED | Sensitive PII; financial harm if disclosed |
| Medical records | T4 — RESTRICTED | PHI under HIPAA; requires BAA compliance |
| Case facts containing personal narratives | T4 — RESTRICTED | PII combined with sensitive legal context |
| Attorney-client communications (if attorney user) | T4 — RESTRICTED | Privileged; disclosure waives privilege |
| User credentials, API keys | T4 — RESTRICTED | Authentication material; compromise = full account takeover |

### C. Classification Matrix

```
DATA CLASSIFICATION DECISION TREE

Is the data publicly available or non-sensitive?
├── YES → T1: PUBLIC
└── NO
    ├── Is it platform operational data (no user PII)?
    │   ├── YES → T2: INTERNAL
    │   └── NO
    │       ├── Does it contain PII, PHI, financial data,
    │       │   or privileged communications?
    │       │   ├── YES → T4: RESTRICTED
    │       │   └── NO → T3: CONFIDENTIAL
    │       └── When in doubt → T4: RESTRICTED
    └── Classification is IMMUTABLE once assigned
        (can only be upgraded, never downgraded)
```

### D. Classification Enforcement

- **Automatic classification**: The PII Scrubbing Pipeline (Section 15.3) scans all inbound data and auto-classifies based on content detection
- **Manual override**: Tenant owner can upgrade classification (T3 to T4) but never downgrade
- **Agent awareness**: All 5 agents receive the classification tier of data they are processing and enforce tier-appropriate handling
- **Audit trail**: Every classification decision is logged with timestamp, method (auto/manual), and justification

---

## 15.2 ENCRYPTION ARCHITECTURE

### A. Data in Transit

All data moving between any two components is encrypted with TLS 1.3.

| Connection | Protocol | Additional Controls |
|------------|----------|-------------------|
| Browser to Cloudflare CDN | TLS 1.3 | HSTS headers (`max-age=31536000; includeSubDomains; preload`) |
| Cloudflare to AWS ALB | TLS 1.3 | Origin certificates, authenticated origin pulls |
| FastAPI to Aurora Postgres | TLS 1.3 | `sslmode=verify-full`, certificate validation |
| FastAPI to ElastiCache Redis | TLS 1.3 | `redis://` with TLS, AUTH token |
| FastAPI to Anthropic API | TLS 1.3 | API key in header, no query string tokens |
| FastAPI to MCP Servers | TLS 1.3 | mTLS for self-hosted servers |
| Expo React Native to API | TLS 1.3 | Certificate pinning (see below) |
| Inter-service (ECS tasks) | TLS 1.3 | Service mesh with mTLS |

**HSTS Configuration:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Certificate Pinning (Mobile — Expo React Native):**
```typescript
// Certificate pinning configuration for Expo/React Native
const pinningConfig = {
  'api.ciphergy.ai': {
    includeSubdomains: true,
    pins: [
      { algorithm: 'sha256', value: '<primary-pin-hash>' },
      { algorithm: 'sha256', value: '<backup-pin-hash>' },
    ],
  },
};

// Pinning is enforced via expo-cert-pinner or react-native-ssl-pinning
// Backup pin rotated 30 days before primary expiry
// Pin validation failure = connection rejected + incident logged
```

**HTTP Security Headers (Cloudflare Workers):**
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### B. Data at Rest

| Storage Layer | Encryption Method | Key Management |
|---------------|------------------|----------------|
| Aurora Postgres (full disk) | AES-256 via AWS RDS encryption | AWS-managed KMS key |
| Aurora Postgres (T4 fields) | Application-level AES-256-GCM | Per-tenant KMS CMK |
| ElastiCache Redis | AES-256 encryption at rest | AWS-managed key |
| S3 (document storage) | SSE-S3 (AES-256) default; SSE-KMS for T4 | Per-tenant KMS CMK for T4 |
| ECS Fargate (ephemeral) | Encrypted ephemeral storage | AWS-managed |
| Backups (Aurora snapshots) | AES-256, same as source | Inherited KMS key |
| Secrets Manager | AES-256 | AWS-managed KMS key |

### C. Per-Tenant Encryption (KMS Architecture)

Every tenant receives a unique AWS KMS Customer Master Key (CMK). This key encrypts all T4 (RESTRICTED) data for that tenant. Key destruction = cryptographic deletion of all T4 data.

```
AWS KMS KEY HIERARCHY

Platform Root Key (AWS-managed)
├── Tenant CMK: tenant_001
│   ├── Data Key: case_001 (T4 fields)
│   ├── Data Key: case_002 (T4 fields)
│   └── Data Key: documents_s3 (T4 uploads)
├── Tenant CMK: tenant_002
│   ├── Data Key: case_001 (T4 fields)
│   └── Data Key: documents_s3 (T4 uploads)
└── Platform Operations Key
    ├── Data Key: system_logs
    └── Data Key: aggregate_metrics
```

**Key Rotation Schedule:**
| Key Type | Rotation Interval | Method | Downtime |
|----------|-------------------|--------|----------|
| Tenant CMK | 90 days (automatic) | AWS KMS automatic rotation | Zero — old key versions retained for decryption |
| Data Keys | Per-session (envelope encryption) | Generated per encryption operation | None — ephemeral |
| TLS Certificates | 90 days (Let's Encrypt / ACM) | Automated renewal via ACM | Zero |
| API Keys (Anthropic) | 180 days | Manual rotation via Secrets Manager | Brief — blue-green swap |
| Service Account Tokens | 90 days | Automated via CI/CD pipeline | Zero — overlapping validity |

### D. Application-Level Field Encryption (T4 Data)

T4 (RESTRICTED) fields are encrypted at the application layer before being written to Postgres. This means even a database administrator with full Aurora access cannot read T4 data without the tenant's KMS key.

```sql
-- Schema showing encrypted fields for case data
CREATE TABLE case_facts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    case_id         UUID NOT NULL REFERENCES cases(id),

    -- T3 fields (encrypted at rest by Aurora, readable by app)
    fact_summary    TEXT NOT NULL,
    fact_category   VARCHAR(50) NOT NULL,
    timeline_date   DATE,

    -- T4 fields (application-level encrypted, per-tenant KMS)
    fact_details_encrypted       BYTEA,          -- AES-256-GCM encrypted
    fact_details_iv              BYTEA,          -- Initialization vector
    fact_details_key_id          VARCHAR(100),   -- KMS key ARN reference
    pii_detected                 BOOLEAN DEFAULT FALSE,
    pii_types                    TEXT[],         -- e.g., {'ssn', 'dob', 'financial'}

    -- Metadata
    classification_tier          VARCHAR(12) NOT NULL DEFAULT 'RESTRICTED'
        CHECK (classification_tier IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- T4 evidence storage
CREATE TABLE evidence_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    case_id         UUID NOT NULL REFERENCES cases(id),

    -- T3 fields
    evidence_type   VARCHAR(50) NOT NULL,       -- 'document', 'photo', 'email', etc.
    exhibit_number  VARCHAR(20),
    description     TEXT,

    -- T4 fields (application-level encrypted)
    content_encrypted            BYTEA,
    content_iv                   BYTEA,
    content_key_id               VARCHAR(100),
    s3_object_key_encrypted      BYTEA,         -- Even the S3 path is encrypted
    s3_object_key_iv             BYTEA,
    original_filename_encrypted  BYTEA,
    original_filename_iv         BYTEA,

    -- Metadata
    classification_tier          VARCHAR(12) NOT NULL DEFAULT 'RESTRICTED',
    file_hash                    VARCHAR(64),    -- SHA-256 of original file
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Encryption Implementation (Python / FastAPI):**
```python
# Envelope encryption using AWS KMS + AES-256-GCM
import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class TenantEncryption:
    def __init__(self, tenant_id: str):
        self.kms = boto3.client('kms')
        self.tenant_key_id = self._get_tenant_key(tenant_id)

    def encrypt_field(self, plaintext: str) -> tuple[bytes, bytes, str]:
        """Encrypt a T4 field using envelope encryption."""
        # Generate a data key from the tenant's CMK
        response = self.kms.generate_data_key(
            KeyId=self.tenant_key_id,
            KeySpec='AES_256'
        )
        data_key = response['Plaintext']
        encrypted_data_key = response['CiphertextBlob']

        # Encrypt the field with the data key
        iv = os.urandom(12)  # 96-bit IV for GCM
        aesgcm = AESGCM(data_key)
        ciphertext = aesgcm.encrypt(iv, plaintext.encode(), None)

        return ciphertext, iv, self.tenant_key_id

    def decrypt_field(self, ciphertext: bytes, iv: bytes, key_id: str) -> str:
        """Decrypt a T4 field."""
        # Retrieve the data key from KMS
        response = self.kms.decrypt(KeyId=key_id, CiphertextBlob=ciphertext)
        data_key = response['Plaintext']

        aesgcm = AESGCM(data_key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode()
```

---

## 15.3 PII SCRUBBING PIPELINE (5 Stages)

Every piece of data entering Ciphergy passes through a 5-stage PII scrubbing pipeline. The pipeline detects, tags, redacts, filters, and audits all personally identifiable information.

### A. Pipeline Architecture

```
USER INPUT (case facts, evidence, documents, communications)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: INPUT SCANNING                                    │
│  Detect PII before it enters agent context                  │
│  ├── Regex patterns: SSN, EIN, credit card, phone, email    │
│  ├── NER model: names, addresses, dates of birth            │
│  ├── Financial detection: bank accounts, routing numbers     │
│  └── Medical detection: ICD codes, diagnosis terms, MRNs    │
│  OUTPUT: PII inventory with type tags and locations          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: CONTEXT TAGGING                                   │
│  Mark PII with type tags for downstream handling            │
│  ├── [SSN:***-**-1234] — last 4 digits retained for ID     │
│  ├── [DOB:REDACTED] — full redaction                        │
│  ├── [FINANCIAL:ACCT-REF-001] — tokenized reference         │
│  ├── [MEDICAL:PHI-REF-001] — tokenized reference            │
│  ├── [NAME:PARTY-PLAINTIFF] — role-based substitution       │
│  └── [ADDRESS:LOCATION-REF-001] — tokenized reference       │
│  OUTPUT: Tagged data with PII mapped to tokens              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: AGENT-LEVEL REDACTION                             │
│  Agents work with redacted versions where possible          │
│  ├── Red Team: receives FULLY redacted PII (needs legal     │
│  │   arguments, not personal data)                          │
│  ├── Research Counsel: receives FULLY redacted PII (needs   │
│  │   legal issues, not personal details)                    │
│  ├── Drafting Counsel: receives SELECTIVE PII (needs names  │
│  │   and dates for document drafting, not SSN/financial)    │
│  ├── Lead Counsel: receives SELECTIVE PII (needs party      │
│  │   names and key dates for strategy)                      │
│  └── Compliance Counsel: receives SELECTIVE PII (needs      │
│      deadlines and jurisdiction, not financials)            │
│  OUTPUT: Per-agent redacted context                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: OUTPUT FILTERING                                  │
│  Final check before data leaves the system                  │
│  ├── Re-scan all agent output for leaked PII                │
│  ├── Verify redaction tokens are not resolved in output     │
│  ├── Check LLM responses for hallucinated PII               │
│  ├── Validate no T4 data appears in logs or telemetry       │
│  └── Strip any PII from error messages and stack traces     │
│  OUTPUT: Clean, verified output ready for user              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5: AUDIT LOGGING                                     │
│  Every PII access logged with justification                 │
│  ├── WHO accessed the PII (agent ID, user ID, service)      │
│  ├── WHAT PII was accessed (type, token reference)          │
│  ├── WHEN it was accessed (timestamp, session ID)           │
│  ├── WHY it was accessed (task context, justification)      │
│  ├── OUTCOME (used in output / redacted / blocked)          │
│  └── Logs are IMMUTABLE and retained for 7 years            │
│  OUTPUT: Complete PII access audit trail                    │
└─────────────────────────────────────────────────────────────┘
```

### B. PII Detection Patterns

| PII Type | Detection Method | Action |
|----------|-----------------|--------|
| Social Security Number | Regex: `\d{3}-\d{2}-\d{4}` + context validation | Tokenize, retain last 4 |
| Employer Identification Number | Regex: `\d{2}-\d{7}` + context validation | Tokenize |
| Credit Card Number | Luhn algorithm + regex patterns | Tokenize, retain last 4 |
| Bank Account Number | Context-aware detection (near "account", "routing") | Tokenize |
| Date of Birth | Date near "born", "DOB", "date of birth" context | Redact in agent context |
| Phone Number | Regex: multiple formats + libphonenumber validation | Tokenize |
| Email Address | RFC 5322 regex | Preserve for party ID, redact from agents |
| Physical Address | NER model + USPS address validation | Tokenize |
| Medical Record Number | Context-aware (near "MRN", "patient ID", medical terms) | Tokenize |
| Driver's License | State-specific format regex + context | Tokenize |
| Passport Number | Country-specific format regex + context | Tokenize |

### C. PII Token Vault

PII tokens (the mapping between `[FINANCIAL:ACCT-REF-001]` and the actual bank account number) are stored in a separate, heavily restricted table with its own encryption:

```sql
CREATE TABLE pii_token_vault (
    token_id        VARCHAR(50) PRIMARY KEY,  -- e.g., 'ACCT-REF-001'
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    pii_type        VARCHAR(30) NOT NULL,     -- 'ssn', 'financial', 'medical', etc.
    pii_value_encrypted  BYTEA NOT NULL,      -- AES-256-GCM encrypted actual value
    pii_value_iv    BYTEA NOT NULL,
    pii_key_id      VARCHAR(100) NOT NULL,    -- Tenant-specific KMS key
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed   TIMESTAMPTZ,
    access_count    INTEGER DEFAULT 0,
    expiry_date     TIMESTAMPTZ               -- Auto-delete after case closure + retention
);

-- Only the document rendering service can resolve tokens to actual values
-- Agents NEVER access this table directly
-- Access requires explicit justification logged in pii_audit_log
```

---

## 15.4 TENANT ISOLATION ARCHITECTURE

### A. Database Isolation (Row-Level Security)

Every table in the system includes `tenant_id`. Postgres Row-Level Security (RLS) enforces that a query can only return rows belonging to the authenticated tenant. This is enforced at the database level — even if application code has a bug, the database will not leak cross-tenant data.

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE deadlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE pii_token_vault ENABLE ROW LEVEL SECURITY;

-- RLS policy: tenant can only see their own data
CREATE POLICY tenant_isolation_select ON cases
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY tenant_isolation_insert ON cases
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY tenant_isolation_update ON cases
    FOR UPDATE
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY tenant_isolation_delete ON cases
    FOR DELETE
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- Applied to EVERY tenant-scoped table (template repeated for each table)
-- Pattern: one SELECT, one INSERT, one UPDATE, one DELETE policy per table

-- Middleware sets tenant context at the start of every transaction
-- FastAPI dependency injection:
--   SET LOCAL app.current_tenant_id = '<tenant_id_from_jwt>';
```

**FastAPI Tenant Context Middleware:**
```python
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def set_tenant_context(
    session: AsyncSession,
    tenant_id: str  # Extracted from JWT claims
):
    """Set RLS context for every database transaction."""
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": tenant_id}
    )
    # Every subsequent query in this transaction is tenant-scoped
    # Even raw SQL queries are constrained by RLS
```

### B. Storage Isolation (S3)

| Tier | Storage Pattern | Access Control |
|------|----------------|----------------|
| Free/Pro | `s3://ciphergy-data/{tenant_id}/{case_id}/` | IAM policy scoped to tenant prefix |
| Team | `s3://ciphergy-data/{tenant_id}/{case_id}/` | IAM policy + bucket policy enforcement |
| Enterprise | `s3://ciphergy-{tenant_id}/` (dedicated bucket) | Dedicated bucket + VPC endpoint |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TenantIsolation",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::ciphergy-data/${aws:PrincipalTag/tenant_id}/*"
    },
    {
      "Sid": "DenyOtherTenants",
      "Effect": "Deny",
      "Action": "s3:*",
      "NotResource": "arn:aws:s3:::ciphergy-data/${aws:PrincipalTag/tenant_id}/*"
    }
  ]
}
```

### C. API Isolation (JWT-Scoped)

Every API request carries a JWT with tenant-scoped claims:

```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "roles": ["owner"],
  "permissions": ["cases:read", "cases:write", "evidence:read", "evidence:write"],
  "iss": "ciphergy.ai",
  "exp": 1742083200,
  "iat": 1742079600
}
```

**Middleware enforcement chain:**
1. Cloudflare WAF validates request structure
2. FastAPI extracts and validates JWT signature (RS256)
3. Tenant ID from JWT is set in database session (`SET LOCAL`)
4. Every route handler receives the tenant-scoped session
5. Response headers never include tenant IDs or internal identifiers

### D. Log Isolation

```
LOG FORMAT (structured JSON):
{
  "timestamp": "2026-03-15T14:30:00Z",
  "level": "INFO",
  "service": "agent-orchestrator",
  "tenant_id": "tenant_uuid",          // Tenant-tagged
  "request_id": "req_uuid",
  "message": "Agent run completed",
  "agent": "research_counsel",
  "duration_ms": 4200,
  // NEVER include: case facts, PII, evidence content, user input
}
```

- Logs are tagged with `tenant_id` for filtering
- CloudWatch log groups are queryable only with tenant-scoped IAM policies
- T4 data is NEVER written to logs — the logging middleware strips any field matching PII patterns
- Log retention: 90 days operational, 7 years for audit/compliance logs

### E. Network Isolation (Enterprise Tier)

```
ENTERPRISE VPC ARCHITECTURE

┌──────────────────────────────────────────────────────────────┐
│  ENTERPRISE TENANT VPC (10.0.0.0/16)                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  PRIVATE SUBNET (10.0.1.0/24)                       │     │
│  │  ├── ECS Fargate Tasks (dedicated capacity)         │     │
│  │  ├── Aurora Postgres (dedicated instance)           │     │
│  │  └── ElastiCache Redis (dedicated node)             │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  VPC ENDPOINTS                                       │     │
│  │  ├── S3 Gateway Endpoint (no internet transit)      │     │
│  │  ├── KMS Interface Endpoint                         │     │
│  │  ├── Secrets Manager Interface Endpoint             │     │
│  │  └── CloudWatch Logs Interface Endpoint             │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  NAT GATEWAY (outbound only)                         │     │
│  │  └── Anthropic API calls (TLS 1.3)                  │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  Security Groups:                                            │
│  ├── ECS: inbound 443 from ALB only; outbound 5432, 6379   │
│  ├── Aurora: inbound 5432 from ECS SG only                  │
│  ├── Redis: inbound 6379 from ECS SG only                   │
│  └── No public IP on any resource                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 15.5 LLM PROVIDER DATA HANDLING

### A. Anthropic API Data Policies

Ciphergy's primary (and for the Legal Litigation Pack, exclusive) LLM provider is Anthropic. The following data handling guarantees apply:

| Policy | Anthropic API (Default) | Ciphergy Configuration |
|--------|------------------------|----------------------|
| Training on API data | **No** — API data is not used for model training | Default; no action required |
| Data retention (logs) | 30 days (abuse monitoring) | Opt-out requested; minimum retention selected |
| Business Associate Agreement | Available | **Executed** — required for HIPAA compliance |
| Data residency | US-based infrastructure | Confirmed US; no cross-border transfer |
| Zero-retention option | Available for enterprise | Enabled for Enterprise tier tenants |
| Prompt caching | Cached for session duration only | Cache TTL set to session; cleared on logout |
| Subprocessors | Published list with notification of changes | Monitored; changes reviewed by Compliance |

### B. Data Flow: What Goes to the LLM

```
CIPHERGY DATA FLOW TO ANTHROPIC API

SENT TO ANTHROPIC:                    NEVER SENT TO ANTHROPIC:
┌──────────────────────────┐         ┌──────────────────────────┐
│ Agent system prompts     │         │ Raw user credentials     │
│ (cached, no PII)         │         │ Payment information      │
│                          │         │ Full SSNs / financial    │
│ Case facts (redacted     │         │   account numbers        │
│   per Stage 3 pipeline)  │         │ Encryption keys          │
│                          │         │ Other tenants' data      │
│ Legal questions /        │         │ Platform infrastructure  │
│   research queries       │         │   details                │
│                          │         │ Audit logs               │
│ Draft content for        │         │ Internal system metrics  │
│   agent review           │         │                          │
│                          │         │ PII token vault contents │
│ Redacted evidence        │         │   (tokens only, not      │
│   descriptions           │         │    actual values)        │
│                          │         │                          │
│ Jurisdiction / court     │         │ Medical record contents  │
│   information            │         │   (tokenized references  │
│                          │         │    only)                 │
│ WDC debate context       │         │                          │
│   (scores, reasoning)    │         │                          │
└──────────────────────────┘         └──────────────────────────┘
```

### C. Provider Data Handling Comparison

| Provider | Training on API Data | Retention | BAA | Zero-Retention Option | Ciphergy Use |
|----------|---------------------|-----------|-----|----------------------|-------------|
| **Anthropic** | No | 30 days (opt-out available) | Yes | Yes (Enterprise) | PRIMARY — All Legal Pack agents |
| OpenAI | No (API default) | 30 days (opt-out available) | Yes | Yes (Enterprise) | FALLBACK ONLY — non-legal packs |
| Google Vertex | No (customer data) | Configurable | Yes | Yes | FUTURE — Construction Pack option |
| AWS Bedrock | No | Configurable | Yes (via AWS BAA) | Yes | FUTURE — VPC-deployed option |

### D. Enterprise VPC Deployment Option

For Enterprise tier tenants where data must never leave the tenant's cloud:

```
ENTERPRISE VPC DEPLOYMENT

Tenant's AWS Account
├── Bedrock (Claude via AWS Bedrock)
│   └── Data never leaves tenant VPC
├── Ciphergy Application (ECS Fargate)
│   └── Deployed in tenant's VPC
├── Aurora Postgres
│   └── Tenant-owned, tenant-encrypted
├── S3
│   └── Tenant-owned bucket
└── KMS
    └── Tenant-owned CMK (they control the keys)

RESULT: Zero data egress to Ciphergy infrastructure
        Tenant owns all data, all keys, all infrastructure
        Ciphergy provides the application layer only
```

---

## 15.6 COMPLIANCE FRAMEWORK

### A. HIPAA Compliance

Medical records routinely enter the legal system: personal injury cases, family law, disability claims, workers' compensation. Ciphergy must handle Protected Health Information (PHI) in compliance with HIPAA.

| HIPAA Requirement | CFR Citation | Ciphergy Implementation |
|-------------------|-------------|------------------------|
| **Business Associate Agreement** | 45 CFR 164.502(e), 164.504(e) | BAA executed with Anthropic; BAA available for Enterprise tenants |
| **Encryption (transmission)** | 45 CFR 164.312(e)(1) | TLS 1.3 on all connections (Section 15.2.A) |
| **Encryption (at rest)** | 45 CFR 164.312(a)(2)(iv) | AES-256 at rest + field-level encryption for PHI (Section 15.2.D) |
| **Access controls** | 45 CFR 164.312(a)(1) | RBAC + RLS + JWT-scoped access (Section 15.4) |
| **Audit controls** | 45 CFR 164.312(b) | Complete audit trail of PHI access (Section 15.3, Stage 5) |
| **Integrity controls** | 45 CFR 164.312(c)(1) | SHA-256 hashes on all stored PHI; tamper detection |
| **Automatic logoff** | 45 CFR 164.312(a)(2)(iii) | Session timeout: 30 minutes inactive; 8 hours maximum |
| **Unique user identification** | 45 CFR 164.312(a)(2)(i) | UUID per user; no shared accounts; MFA required for PHI access |
| **Emergency access** | 45 CFR 164.312(a)(2)(ii) | Break-glass procedure with post-access audit and notification |
| **Minimum necessary** | 45 CFR 164.502(b) | PII Scrubbing Pipeline ensures agents receive minimum PHI needed |
| **Breach notification** | 45 CFR 164.404-408 | Incident Response Plan (Section 15.8); 60-day notification requirement |
| **PHI disposal** | 45 CFR 164.530(c) | Cryptographic deletion via KMS key destruction (Section 15.7) |

### B. GDPR Compliance

If European users access the platform (or if a US case involves EU data subjects), GDPR applies.

| GDPR Requirement | Article | Ciphergy Implementation |
|-------------------|---------|------------------------|
| **Lawful basis for processing** | Art. 6(1)(b) | Processing necessary for service contract performance |
| **Data minimization** | Art. 5(1)(c) | PII Scrubbing Pipeline (Section 15.3) ensures minimum data processing |
| **Purpose limitation** | Art. 5(1)(b) | Data processed solely for litigation support; no secondary use |
| **Storage limitation** | Art. 5(1)(e) | Retention policies by tier (Section 15.7); auto-deletion schedules |
| **Right to access** | Art. 15 | Full case data export (22-section format) available on demand |
| **Right to rectification** | Art. 16 | User can update personal data via settings; propagates to all records |
| **Right to erasure** | Art. 17 | Account deletion workflow with cryptographic deletion (Section 15.7) |
| **Right to data portability** | Art. 20 | Export in structured, machine-readable JSON format |
| **Data protection by design** | Art. 25 | Encryption, RLS, PII scrubbing are architectural, not bolt-ons |
| **Data Protection Impact Assessment** | Art. 35 | DPIA completed; high-risk processing documented |
| **Data Processing Agreement** | Art. 28 | DPA executed with all subprocessors (Anthropic, AWS, Cloudflare) |
| **Breach notification (authority)** | Art. 33 | 72-hour notification to supervisory authority |
| **Breach notification (individuals)** | Art. 34 | Without undue delay to affected users if high risk |
| **Data Protection Officer** | Art. 37-39 | DPO appointed; contact published in Privacy Policy |
| **Cross-border transfers** | Art. 46 | Standard Contractual Clauses with EU subprocessors; data stays in US/EU |

### C. CCPA / CPRA Compliance

California users are protected under the California Consumer Privacy Act (as amended by CPRA).

| CCPA/CPRA Requirement | Citation | Ciphergy Implementation |
|-----------------------|----------|------------------------|
| **Right to know** | Cal. Civ. Code 1798.100 | Privacy dashboard shows all data categories collected |
| **Right to delete** | Cal. Civ. Code 1798.105 | Account deletion with cryptographic deletion (Section 15.7) |
| **Right to opt-out of sale** | Cal. Civ. Code 1798.120 | N/A — Ciphergy does not sell personal information. "Do Not Sell" link provided regardless. |
| **Right to correct** | Cal. Civ. Code 1798.106 | User can correct personal data via settings |
| **Right to limit use of sensitive PI** | Cal. Civ. Code 1798.121 | Sensitive PI (SSN, financial, medical) restricted to T4 tier with maximum protections |
| **Non-discrimination** | Cal. Civ. Code 1798.125 | No service degradation for exercising privacy rights |
| **Notice at collection** | Cal. Civ. Code 1798.100(b) | Privacy notice displayed at signup; categories listed |
| **Data processing agreements** | Cal. Civ. Code 1798.100(d) | Service provider agreements with all subprocessors |
| **Reasonable security** | Cal. Civ. Code 1798.150 | Encryption, access controls, audit trails (this entire section) |
| **Privacy policy** | Cal. Civ. Code 1798.130(a)(5) | Published; updated annually; includes all required disclosures |

### D. SOC 2 Type II (Phase 8 Deliverable)

SOC 2 Type II certification covers five Trust Service Criteria. Ciphergy targets certification by the end of Phase 8.

| Trust Service Criteria | Scope | Key Controls |
|-----------------------|-------|-------------|
| **Security** | Protection against unauthorized access | MFA, RLS, JWT, WAF, encryption at rest and in transit, DDoS protection |
| **Availability** | System uptime and performance | Multi-AZ deployment, auto-scaling, health checks, incident response |
| **Processing Integrity** | Accurate and complete processing | WDC verification chains, citation verification, PII pipeline validation |
| **Confidentiality** | Protection of confidential data | Encryption, tenant isolation, classification framework, access controls |
| **Privacy** | Personal information handling | GDPR/CCPA compliance, PII scrubbing, data lifecycle management, consent |

**Audit preparation:**
- Evidence collection automated via AWS Config, CloudTrail, and custom audit scripts
- Control testing documented in internal compliance tracker
- Readiness assessment scheduled for Phase 7; formal audit in Phase 8
- Auditor: independent CPA firm with SaaS/legal-tech experience

### E. State Data Breach Notification Requirements

Every US state has its own breach notification law. Ciphergy's Incident Response Plan (Section 15.8) must meet the most stringent requirements.

| State | Statute | Notification Deadline | AG Notification | Notable Requirements |
|-------|---------|----------------------|----------------|---------------------|
| **California** | Cal. Civ. Code 1798.82 | "Expedient, without unreasonable delay" | If >500 CA residents | Must include specific breach details and identity theft prevention services |
| **New York** | N.Y. Gen. Bus. Law 899-aa | "Expedient, without unreasonable delay" | AG, DFS, and State Police | Must disclose timeline of breach and remediation steps |
| **Florida** | Fla. Stat. 501.171 | 30 calendar days | AG if >500 FL residents | One of the shortest deadlines; penalties for late notification |
| **Texas** | Tex. Bus. & Com. Code 521.053 | 60 calendar days | AG if >250 TX residents | Must offer identity theft protection for 12 months |
| **Illinois** | 815 ILCS 530/10 | "Most expedient time possible" | AG required | BIPA (biometric) has separate requirements with private right of action |
| **Louisiana** | La. R.S. 51:3074 | 60 calendar days | AG required | Written notification required; electronic insufficient alone |
| **Georgia** | O.C.G.A. 10-1-912 | "Most expedient time possible" | Required | Must notify consumer reporting agencies if >10,000 residents |
| **Ohio** | O.R.C. 1349.19 | 45 calendar days | AG required | Safe harbor for encrypted data if key not compromised |
| **Pennsylvania** | 73 P.S. 2303 | "Without unreasonable delay" | AG required | Must disclose method of notification and contact information |
| **Virginia** | Va. Code 18.2-186.6 | 60 calendar days | AG and State Police | Must provide free credit monitoring for 12 months |

**Implementation:** The `breach_notifications` table (Section 15.10) tracks per-state requirements, deadlines, and notification status. Compliance Counsel's incident response workflow auto-populates required notifications based on affected users' states (derived from geo-location data collected at signup per Section 14.1).

### F. Compliance Matrix (Summary)

```
CIPHERGY COMPLIANCE MATRIX

                    HIPAA   GDPR   CCPA   SOC2   State Breach
                    ─────   ────   ────   ────   ────────────
Encryption (TLS)     [x]    [x]    [x]    [x]      [x]
Encryption (rest)    [x]    [x]    [x]    [x]      [x]
Access Controls      [x]    [x]    [x]    [x]      [x]
Audit Trails         [x]    [x]    [x]    [x]      [x]
Breach Response      [x]    [x]    [x]    [x]      [x]
Data Minimization    [x]    [x]    [x]    [x]      ---
Right to Delete      [x]    [x]    [x]    [x]      ---
Data Portability     ---    [x]    [x]    ---      ---
BAA / DPA            [x]    [x]    [x]    ---      ---
Incident Plan        [x]    [x]    [x]    [x]      [x]
Regular Audits       [x]    [x]    ---    [x]      ---
Employee Training    [x]    [x]    [x]    [x]      ---

[x] = Required and implemented
--- = Not applicable to this regulation
```

---

## 15.7 DATA LIFECYCLE MANAGEMENT

### A. Retention Policy by Classification Tier

| Tier | Active Retention | Archive Retention | Total | Deletion Method |
|------|-----------------|-------------------|-------|----------------|
| T1: PUBLIC | Indefinite | N/A | Indefinite | Standard deletion |
| T2: INTERNAL | 1 year | 2 years | 3 years | Standard deletion + log purge |
| T3: CONFIDENTIAL | Active case + 7 years | None | Case duration + 7 years | Secure deletion (overwrite) |
| T4: RESTRICTED | Active case + 7 years | None | Case duration + 7 years | Cryptographic deletion (key destruction) |

**Why 7 years for T3/T4:** Legal document retention standards in most US jurisdictions recommend 5-7 years for litigation files. The IRS requires 7 years for tax-related documents. State bar associations generally recommend 7 years from case closure. Ciphergy defaults to 7 years to satisfy the most conservative requirement.

### B. Cryptographic Deletion

For T4 (RESTRICTED) data, deletion means destroying the encryption key. Without the key, the ciphertext is computationally irreversible.

```
CRYPTOGRAPHIC DELETION WORKFLOW

User requests account deletion
         │
         ▼
    VERIFICATION (multi-factor)
    ├── Email confirmation link
    ├── Password re-entry
    └── 72-hour cooling period (can cancel)
         │
         ▼
    DATA EXPORT OFFER
    ├── "Download all your data before deletion"
    ├── Full 22-section case extraction (JSON + PDF)
    └── Evidence files (ZIP archive)
         │
         ▼
    DELETION EXECUTION (after 72-hour cooling period)
    ├── Step 1: Delete S3 objects (documents, evidence)
    ├── Step 2: Delete Postgres rows (case data, PII vault)
    ├── Step 3: Destroy tenant KMS CMK (irreversible)
    │           └── All T4 ciphertext becomes unrecoverable
    ├── Step 4: Purge Redis cache entries
    ├── Step 5: Purge CloudWatch logs containing tenant_id
    │           └── Retention: only anonymized aggregate metrics survive
    ├── Step 6: Mark user record as DELETED (retain only:
    │           user_id, deletion_date, deletion_method)
    └── Step 7: Generate deletion certificate
         │
         ▼
    DELETION CERTIFICATE
    ├── "All data associated with account [user_id] has been
    │    permanently deleted as of [timestamp]."
    ├── KMS key ARN: [destroyed]
    ├── S3 objects deleted: [count]
    ├── Database rows deleted: [count]
    ├── Signed by system with timestamp
    └── Emailed to user's registered email address
```

### C. Right to Be Forgotten Implementation

GDPR Article 17 and CCPA 1798.105 require the ability to erase personal data. Ciphergy's implementation:

1. **User-initiated**: Settings > Privacy > "Delete My Account and All Data"
2. **72-hour cooling period**: Prevents impulsive deletion of active case data
3. **Data export before deletion**: Automatic offer; user can download everything
4. **Subprocessor notification**: Anthropic, AWS are notified to purge any cached data
5. **Third-party data**: If case data was shared via API webhooks, recipients are notified of deletion request
6. **Confirmation**: Deletion certificate with cryptographic proof (KMS key destruction record)
7. **Exceptions**: Data required for legal compliance (e.g., billing records for tax purposes) retained in anonymized form for the legally required period

### D. Data Export (Full Case Extraction)

Users can export all their data at any time. This serves both GDPR Article 20 (data portability) and Ciphergy's own philosophy: "Your case data is yours."

**Export Format:**
```
ciphergy_export_{user_id}_{timestamp}/
├── metadata.json                    -- Export metadata, version, timestamp
├── user_profile.json                -- User data (name, email, settings)
├── cases/
│   ├── case_001/
│   │   ├── executive_summary.md     -- Section 1: Full case summary
│   │   ├── parties.json             -- Section 2: All parties
│   │   ├── timeline.json            -- Section 3: Complete timeline
│   │   ├── claims.json              -- Section 4: All claims with elements
│   │   ├── defenses.json            -- Section 5: Defenses analysis
│   │   ├── risk_analysis.json       -- Section 6: Risk assessment
│   │   ├── evidence/                -- Section 7: All evidence files
│   │   │   ├── inventory.json
│   │   │   └── files/               -- Original uploaded documents
│   │   ├── discovery.json           -- Section 8: Discovery log
│   │   ├── motions.json             -- Section 9: Motion history
│   │   ├── authorities.json         -- Section 10: Citations (VAR entries)
│   │   ├── work_product/            -- Section 11: All generated documents
│   │   ├── strategy.json            -- Section 12: Strategy documents
│   │   ├── communications.json      -- Section 13: Correspondence log
│   │   ├── financials.json          -- Section 14: Financial data
│   │   ├── jurisdiction.json        -- Section 15: Jurisdiction config
│   │   ├── deadlines.json           -- Section 18: All deadlines
│   │   ├── wdc_debate_logs.json     -- Full WDC audit trail
│   │   └── agent_run_history.json   -- All agent interactions
│   └── case_002/
│       └── ...
├── billing_history.json             -- Payment records (anonymized)
└── export_manifest.json             -- SHA-256 hashes of all files
```

### E. Account Closure Workflow

```
ACCOUNT CLOSURE PROCESS

Step 1: USER REQUESTS CLOSURE
        └── Settings > Account > Close Account

Step 2: ACTIVE CASE CHECK
        ├── If active cases with upcoming deadlines:
        │   └── WARNING: "You have [N] active cases with deadlines
        │       in the next 30 days. Closing your account will
        │       delete all case data permanently."
        └── User must acknowledge explicitly

Step 3: DATA EXPORT
        ├── Auto-generate full export (all cases)
        ├── Download link emailed (valid 30 days)
        └── User can download before proceeding

Step 4: COOLING PERIOD (72 hours)
        ├── Account marked as PENDING_CLOSURE
        ├── Full functionality retained during cooling period
        ├── Can cancel at any time during this window
        └── Daily email reminders: "Your account will be deleted in [N] days"

Step 5: FINAL DELETION
        ├── Cryptographic deletion (Section 15.7.B)
        ├── Deletion certificate generated
        └── Confirmation email sent

Step 6: POST-DELETION
        ├── Anonymized aggregate metrics retained (no PII)
        ├── Billing records retained per tax requirements (7 years)
        │   └── Anonymized: amount, date, subscription tier only
        └── No re-creation with same email for 30 days (fraud prevention)
```

---

## 15.8 INCIDENT RESPONSE PLAN

### A. Severity Classification

| Severity | Label | Definition | Examples |
|----------|-------|------------|---------|
| **P0** | DATA BREACH | Confirmed unauthorized access to or exfiltration of user data | Database compromise, credential leak, unauthorized data export, ransomware |
| **P1** | UNAUTHORIZED ACCESS ATTEMPT | Attempted but blocked access; no data exfiltration confirmed | Brute force attack, credential stuffing, SQL injection attempt (blocked), privilege escalation attempt |
| **P2** | CONFIGURATION ERROR | Security misconfiguration that could lead to exposure if exploited | Open S3 bucket, overly permissive IAM role, expired TLS certificate, missing RLS policy |
| **P3** | MINOR VULNERABILITY | Low-severity vulnerability identified but not exploited | Outdated dependency with known CVE (no exploit path), informational security header missing |

### B. Response Procedures

**P0 — DATA BREACH (Response: Immediate)**

```
P0 INCIDENT RESPONSE TIMELINE

T+0 min    DETECTION
           ├── Automated alert (WAF, CloudTrail, anomaly detection)
           │   OR user report OR security researcher disclosure
           └── Incident commander assigned (on-call engineer)

T+15 min   CONTAINMENT
           ├── Isolate affected systems (network segmentation)
           ├── Revoke compromised credentials
           ├── Enable enhanced logging on affected systems
           ├── Preserve forensic evidence (snapshot affected instances)
           └── DO NOT delete logs or modify affected systems

T+30 min   ASSESSMENT
           ├── Determine scope: which tenants affected?
           ├── Determine data types: T1/T2/T3/T4?
           ├── Determine vector: how did they get in?
           ├── Determine duration: how long was access active?
           └── Begin affected user enumeration

T+1 hr     ESCALATION
           ├── Notify executive team
           ├── Engage legal counsel (external, if needed)
           ├── Engage forensics firm (if scope warrants)
           └── Begin breach notification countdown (state-specific)

T+4 hr     ERADICATION
           ├── Patch vulnerability or close attack vector
           ├── Rotate all potentially compromised keys/credentials
           ├── Re-deploy affected services from clean images
           └── Verify containment is holding

T+24 hr    NOTIFICATION (if T4 data confirmed exposed)
           ├── Notify affected users (email + in-app)
           ├── Notify state AGs per state-specific deadlines
           ├── Notify HHS if PHI involved (HIPAA: 60 days max)
           ├── Notify GDPR supervisory authority (72 hours max)
           └── Publish incident notice on status page

T+72 hr    RECOVERY
           ├── Restore full service from verified-clean state
           ├── Enhanced monitoring for 30 days
           ├── Offer affected users: password reset, credit monitoring
           └── Verify no residual unauthorized access

T+7 days   POST-INCIDENT REVIEW
           ├── Root cause analysis document
           ├── Timeline reconstruction
           ├── ERROR_MUSEUM entry (per Phase 7 protocol)
           ├── Control improvements identified and scheduled
           └── Report to board / investors if material
```

**P1 — UNAUTHORIZED ACCESS ATTEMPT (Response: 1 hour)**
1. Review WAF/IDS logs to confirm attempt was blocked
2. Identify source (IP, user agent, attack pattern)
3. Block source at WAF level (Cloudflare IP block, rate limit rule)
4. Verify no data was accessed (audit trail review)
5. If pattern suggests targeted attack: escalate to P0 procedures
6. Document in security incident log

**P2 — CONFIGURATION ERROR (Response: 4 hours)**
1. Assess exposure window (when was it misconfigured?)
2. Remediate immediately (close bucket, tighten IAM, renew cert)
3. Audit for exploitation during exposure window
4. If exploitation found: escalate to P1 or P0
5. Add automated check to prevent recurrence (AWS Config rule)
6. Document and add to deployment checklist

**P3 — MINOR VULNERABILITY (Response: 48 hours)**
1. Assess exploitability in Ciphergy's specific context
2. If exploitable: upgrade to P2; remediate immediately
3. If not exploitable: schedule fix in next release cycle
4. Update dependency or configuration
5. Verify fix in staging environment
6. Document in vulnerability tracker

### C. Severity Matrix

```
INCIDENT SEVERITY DETERMINATION

                        DATA ACCESSED
                    ┌──────────┬──────────┐
                    │    NO    │   YES    │
         ┌──────────┼──────────┼──────────┤
ATTACK   │ BLOCKED  │   P1     │   P0     │
SUCCESS  ├──────────┼──────────┼──────────┤
         │ PARTIAL  │   P1     │   P0     │
         ├──────────┼──────────┼──────────┤
         │ UNKNOWN  │   P1*    │   P0     │
         └──────────┴──────────┴──────────┘

         * Treat as P0 until confirmed otherwise

CONFIG   │ EXPLOITED│   P0     │   P0     │
ERROR    │ EXPOSED  │   P2     │   P0     │
         │ INTERNAL │   P3     │   P2     │
```

### D. Post-Incident: ERROR_MUSEUM Entry

Every P0 and P1 incident produces an ERROR_MUSEUM entry (per Phase 7 hardening protocol):

```yaml
error_museum_entry:
  id: "SEC-2026-001"
  severity: "P0"
  title: "Descriptive title of the incident"
  date_detected: "2026-XX-XX"
  date_resolved: "2026-XX-XX"
  attack_vector: "How they got in"
  root_cause: "Why the attack vector existed"
  data_exposed: "What data was accessed (classification tiers)"
  users_affected: N
  detection_method: "How we found out"
  detection_delay: "Time from breach to detection"
  containment_actions: ["List of immediate actions taken"]
  remediation: "What was fixed"
  prevention: "What controls were added to prevent recurrence"
  lessons_learned: "What we will do differently"
  controls_added:
    - "Specific control 1"
    - "Specific control 2"
```

---

## 15.9 NETWORK & INFRASTRUCTURE SECURITY

### A. VPC Architecture

```
CIPHERGY PRODUCTION NETWORK ARCHITECTURE

                    INTERNET
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  CLOUDFLARE (CDN + WAF + DDoS Protection)                    │
│  ├── WAF Rules (see 15.9.B)                                 │
│  ├── DDoS Protection (Enterprise)                           │
│  ├── Rate Limiting (Layer 1 of 4)                           │
│  ├── Bot Management                                         │
│  └── Cloudflare Pages (static frontend assets)              │
└──────────────────────┬───────────────────────────────────────┘
                       │ (Authenticated origin pull, TLS 1.3)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  AWS VPC (10.0.0.0/16)                                       │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │  PUBLIC SUBNET (10.0.1.0/24, 10.0.2.0/24)         │      │
│  │  ├── Application Load Balancer (ALB)               │      │
│  │  │   ├── TLS termination (ACM certificate)         │      │
│  │  │   ├── Health checks: /health (5s interval)      │      │
│  │  │   └── Target group: ECS Fargate tasks           │      │
│  │  └── NAT Gateway (outbound internet for APIs)      │      │
│  └─────────────────────┬──────────────────────────────┘      │
│                        │                                     │
│  ┌─────────────────────▼──────────────────────────────┐      │
│  │  PRIVATE SUBNET — APPLICATION (10.0.10.0/24)       │      │
│  │  ├── ECS Fargate: FastAPI application               │      │
│  │  │   ├── Task CPU/memory limits enforced            │      │
│  │  │   ├── Read-only root filesystem                  │      │
│  │  │   ├── No SSH access (no EC2, no bastion)         │      │
│  │  │   └── IAM task role (least privilege)             │      │
│  │  ├── ECS Fargate: Agent Orchestrator                │      │
│  │  ├── ECS Fargate: MCP Server Runner                 │      │
│  │  └── ECS Fargate: Document Generation Service       │      │
│  └─────────────────────┬──────────────────────────────┘      │
│                        │                                     │
│  ┌─────────────────────▼──────────────────────────────┐      │
│  │  PRIVATE SUBNET — DATA (10.0.20.0/24)              │      │
│  │  ├── Aurora Postgres (Multi-AZ)                     │      │
│  │  │   ├── No public endpoint                         │      │
│  │  │   ├── Security group: inbound 5432 from app SG   │      │
│  │  │   └── Encrypted storage (AES-256)                │      │
│  │  ├── ElastiCache Redis (Multi-AZ)                   │      │
│  │  │   ├── No public endpoint                         │      │
│  │  │   ├── Security group: inbound 6379 from app SG   │      │
│  │  │   ├── AUTH token required                        │      │
│  │  │   └── Encryption in transit + at rest            │      │
│  │  └── S3 VPC Endpoint (gateway — no internet)        │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  SECURITY GROUPS:                                            │
│  ├── sg-alb:    inbound 443 from Cloudflare IPs only        │
│  ├── sg-app:    inbound from sg-alb only; outbound to       │
│  │              sg-data + NAT (for Anthropic API)            │
│  ├── sg-aurora: inbound 5432 from sg-app only               │
│  └── sg-redis:  inbound 6379 from sg-app only               │
└──────────────────────────────────────────────────────────────┘
```

### B. WAF Rules (Cloudflare)

| Rule | Action | Purpose |
|------|--------|---------|
| OWASP Core Rule Set | Block/Challenge | SQL injection, XSS, LFI/RFI, command injection |
| Rate limiting (global) | 1000 req/min per IP | DDoS mitigation |
| Rate limiting (auth) | 10 req/min per IP | Brute force prevention |
| Rate limiting (API) | Per-tenant budget (from JWT) | Cost control + abuse prevention |
| Geographic blocking | Block (configurable) | OFAC-sanctioned countries |
| Bot management | Challenge/Block | Credential stuffing, scraping |
| Custom rule: SQL in URL | Block | Defense-in-depth for injection |
| Custom rule: Large body | Block >10MB | Prevent resource exhaustion |
| Custom rule: API versioning | Block unversioned | Force clients to use versioned API |

### C. DDoS Protection

| Layer | Protection | Provider |
|-------|-----------|----------|
| L3/L4 (Network) | Automatic DDoS mitigation | Cloudflare (always-on) |
| L7 (Application) | Rate limiting + bot management | Cloudflare + application-level |
| API | Per-tenant rate limits (4-layer from V2) | FastAPI middleware + Redis |
| Database | Connection pooling (PgBouncer) + query timeouts | Aurora + application |

### D. API Rate Limiting (4-Layer Architecture from V2 Spec)

```
LAYER 1: Cloudflare Rate Limiting
         └── Per-IP limits (1000 req/min global, 10 req/min auth)

LAYER 2: Redis Rate Limiter (FastAPI middleware)
         └── Per-user and per-tenant RPM on API endpoints
         └── Sliding window algorithm

LAYER 3: Token Budget Tracking
         └── Pre-request estimation + post-request recording
         └── Per-tenant monthly caps (soft warning + hard block)

LAYER 4: Agent Loop Protection
         └── 25 max iterations per agent run
         └── Per-run token budget
         └── Execution timeouts (300s default, 600s max)
         └── Circuit breakers on consecutive errors (3 failures = pause)
```

### E. Container Security (ECS Fargate)

| Control | Implementation |
|---------|---------------|
| Base image | AWS-managed Fargate platform (no OS management) |
| Image scanning | ECR image scanning on push (CVE detection) |
| Root filesystem | Read-only (`readonlyRootFilesystem: true`) |
| Privilege escalation | Disabled (`privileged: false`) |
| Network mode | `awsvpc` (each task gets its own ENI) |
| Secrets | Injected via Secrets Manager reference (never in env vars) |
| Logging | stdout/stderr to CloudWatch (no local log files) |
| Resource limits | CPU and memory hard limits per task definition |
| IAM role | Task-specific IAM role with least privilege |
| No SSH | No shell access — debugging via CloudWatch Logs + X-Ray |

### F. Secrets Management (AWS Secrets Manager)

| Secret | Rotation | Access |
|--------|----------|--------|
| Anthropic API Key | 180 days | Agent Orchestrator task role only |
| Database credentials | 90 days (automatic via Secrets Manager) | Application task role only |
| Redis AUTH token | 90 days | Application task role only |
| JWT signing key (RS256) | Annual (key pair rotation) | Application task role only |
| S3 access | IAM role-based (no static keys) | Task role with tenant-scoped policy |
| Stripe API key | 180 days | Billing service task role only |
| MCP server tokens | 90 days | MCP Runner task role only |

**Secret access pattern:**
```python
# Secrets are never in environment variables or code
# Retrieved at startup via AWS SDK, cached in memory, refreshed on rotation
import boto3

def get_secret(secret_name: str) -> str:
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Usage in FastAPI lifespan
ANTHROPIC_API_KEY = get_secret('ciphergy/prod/anthropic-api-key')
DATABASE_URL = get_secret('ciphergy/prod/database-url')
```

---

## 15.10 SECURITY DATABASE SCHEMAS

### Schema 1: Encryption Key Metadata

```sql
-- Per-tenant encryption key tracking
CREATE TABLE encryption_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    key_type        VARCHAR(30) NOT NULL,  -- 'tenant_cmk', 'data_key', 'backup_key'
    aws_key_arn     VARCHAR(256) NOT NULL, -- Full ARN of the KMS key
    key_status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (key_status IN ('ACTIVE', 'ROTATING', 'PENDING_DELETION', 'DESTROYED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_rotated_at TIMESTAMPTZ,
    next_rotation   TIMESTAMPTZ,          -- Scheduled rotation date
    rotation_count  INTEGER DEFAULT 0,
    destroyed_at    TIMESTAMPTZ,          -- Set when key is destroyed (crypto deletion)
    destruction_reason VARCHAR(100),       -- 'account_closure', 'key_rotation', 'security_incident'
    destruction_certificate TEXT,          -- Signed deletion certificate

    CONSTRAINT unique_active_key UNIQUE (tenant_id, key_type, key_status)
);

CREATE INDEX idx_encryption_keys_tenant ON encryption_keys(tenant_id);
CREATE INDEX idx_encryption_keys_status ON encryption_keys(key_status);
CREATE INDEX idx_encryption_keys_rotation ON encryption_keys(next_rotation)
    WHERE key_status = 'ACTIVE';
```

### Schema 2: PII Audit Log

```sql
-- Every PII access is logged immutably
CREATE TABLE pii_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID REFERENCES users(id),       -- NULL if system/agent access
    agent_id        VARCHAR(50),                      -- 'lead_counsel', 'research_counsel', etc.
    session_id      UUID NOT NULL,
    request_id      UUID NOT NULL,

    -- What was accessed
    pii_type        VARCHAR(30) NOT NULL,             -- 'ssn', 'dob', 'financial', 'medical', etc.
    pii_token_id    VARCHAR(50),                      -- Reference to pii_token_vault
    data_tier       VARCHAR(12) NOT NULL,             -- 'RESTRICTED'

    -- Access details
    access_type     VARCHAR(20) NOT NULL,             -- 'read', 'decrypt', 'export', 'delete'
    access_purpose  TEXT NOT NULL,                    -- 'document_drafting', 'case_export', etc.
    access_granted  BOOLEAN NOT NULL,                 -- Was the access allowed?
    denial_reason   TEXT,                             -- If denied, why

    -- Context
    source_ip       INET,
    user_agent      TEXT,
    api_endpoint    VARCHAR(200),

    -- Immutable timestamp
    accessed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- This table is append-only — no UPDATE or DELETE policies
    -- Enforced via RLS policy that allows INSERT only
    CONSTRAINT no_future_dates CHECK (accessed_at <= NOW() + INTERVAL '1 minute')
);

-- RLS: tenants can only see their own PII audit logs
ALTER TABLE pii_audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY pii_audit_tenant_read ON pii_audit_log
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
CREATE POLICY pii_audit_system_insert ON pii_audit_log
    FOR INSERT WITH CHECK (TRUE);  -- System can log for any tenant
-- No UPDATE or DELETE policies = append-only

CREATE INDEX idx_pii_audit_tenant ON pii_audit_log(tenant_id);
CREATE INDEX idx_pii_audit_session ON pii_audit_log(session_id);
CREATE INDEX idx_pii_audit_type ON pii_audit_log(pii_type);
CREATE INDEX idx_pii_audit_time ON pii_audit_log(accessed_at);
```

### Schema 3: Security Incidents

```sql
-- Security incident tracking and response
CREATE TABLE security_incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_number VARCHAR(20) NOT NULL UNIQUE,     -- 'SEC-2026-001'
    severity        VARCHAR(2) NOT NULL
        CHECK (severity IN ('P0', 'P1', 'P2', 'P3')),
    status          VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'INVESTIGATING', 'CONTAINED', 'ERADICATED',
                          'RECOVERED', 'CLOSED', 'POST_MORTEM')),

    -- Incident details
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    attack_vector   TEXT,
    affected_systems TEXT[],                          -- e.g., {'aurora', 'api', 's3'}
    affected_tenants UUID[],                          -- Which tenants were impacted
    affected_user_count INTEGER DEFAULT 0,

    -- Data impact
    data_accessed   BOOLEAN DEFAULT FALSE,
    data_exfiltrated BOOLEAN DEFAULT FALSE,
    data_tiers_affected VARCHAR(12)[],               -- e.g., {'CONFIDENTIAL', 'RESTRICTED'}
    pii_types_affected VARCHAR(30)[],                -- e.g., {'ssn', 'financial'}

    -- Timeline
    detected_at     TIMESTAMPTZ NOT NULL,
    contained_at    TIMESTAMPTZ,
    eradicated_at   TIMESTAMPTZ,
    recovered_at    TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,

    -- Response
    incident_commander VARCHAR(100),
    root_cause      TEXT,
    remediation_actions TEXT[],
    prevention_controls TEXT[],                       -- Controls added post-incident
    error_museum_id VARCHAR(20),                      -- Reference to ERROR_MUSEUM entry

    -- Metadata
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_security_incidents_severity ON security_incidents(severity);
CREATE INDEX idx_security_incidents_status ON security_incidents(status);
CREATE INDEX idx_security_incidents_detected ON security_incidents(detected_at);
```

### Schema 4: Data Retention Policies

```sql
-- Per-tier data retention configuration
CREATE TABLE data_retention_policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier            VARCHAR(12) NOT NULL UNIQUE
        CHECK (tier IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')),
    active_retention_days   INTEGER NOT NULL,         -- Days in active storage
    archive_retention_days  INTEGER NOT NULL,         -- Days in archive after active
    total_retention_days    INTEGER GENERATED ALWAYS AS
        (active_retention_days + archive_retention_days) STORED,
    deletion_method VARCHAR(30) NOT NULL
        CHECK (deletion_method IN ('STANDARD', 'SECURE_OVERWRITE', 'CRYPTOGRAPHIC')),
    auto_delete     BOOLEAN NOT NULL DEFAULT TRUE,    -- Auto-delete after retention expires
    legal_hold_exempt BOOLEAN NOT NULL DEFAULT FALSE, -- Can legal hold override auto-delete?

    -- Compliance mappings
    hipaa_applicable BOOLEAN DEFAULT FALSE,
    gdpr_applicable  BOOLEAN DEFAULT FALSE,
    ccpa_applicable  BOOLEAN DEFAULT FALSE,

    -- Metadata
    effective_date  DATE NOT NULL,
    approved_by     VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Default retention policies
INSERT INTO data_retention_policies
    (tier, active_retention_days, archive_retention_days, deletion_method,
     auto_delete, legal_hold_exempt, hipaa_applicable, gdpr_applicable,
     ccpa_applicable, effective_date, approved_by)
VALUES
    ('PUBLIC',       36500, 0,   'STANDARD',       FALSE, FALSE, FALSE, FALSE, FALSE, '2026-03-15', 'Bo Pennington'),
    ('INTERNAL',     365,   730, 'STANDARD',       TRUE,  FALSE, FALSE, FALSE, FALSE, '2026-03-15', 'Bo Pennington'),
    ('CONFIDENTIAL', 2555,  0,   'SECURE_OVERWRITE', TRUE, TRUE,  TRUE,  TRUE,  TRUE,  '2026-03-15', 'Bo Pennington'),
    ('RESTRICTED',   2555,  0,   'CRYPTOGRAPHIC',  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  '2026-03-15', 'Bo Pennington');
```

### Schema 5: Breach Notifications

```sql
-- State-specific breach notification tracking
CREATE TABLE breach_notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id     UUID NOT NULL REFERENCES security_incidents(id),

    -- State requirements
    state_code      VARCHAR(2) NOT NULL,              -- US state code
    state_statute   VARCHAR(100) NOT NULL,            -- e.g., 'Cal. Civ. Code 1798.82'
    notification_deadline_days INTEGER NOT NULL,       -- Days from discovery to notify
    notification_deadline_date TIMESTAMPTZ NOT NULL,   -- Calculated absolute deadline
    ag_notification_required BOOLEAN NOT NULL,
    ag_notification_threshold INTEGER,                 -- Min affected residents to notify AG

    -- Notification status
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'DRAFTING', 'REVIEW', 'SENT', 'CONFIRMED', 'EXEMPT')),
    affected_residents_count INTEGER NOT NULL DEFAULT 0,

    -- Notification details
    notification_method VARCHAR(30),                  -- 'email', 'mail', 'substitute'
    notification_sent_at TIMESTAMPTZ,
    ag_notified_at  TIMESTAMPTZ,
    notification_content TEXT,                         -- Template of what was sent
    credit_monitoring_offered BOOLEAN DEFAULT FALSE,
    credit_monitoring_provider VARCHAR(100),

    -- Compliance tracking
    compliant       BOOLEAN,                          -- Was notification sent on time?
    compliance_notes TEXT,

    -- Metadata
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_breach_notifications_incident ON breach_notifications(incident_id);
CREATE INDEX idx_breach_notifications_state ON breach_notifications(state_code);
CREATE INDEX idx_breach_notifications_status ON breach_notifications(status);
CREATE INDEX idx_breach_notifications_deadline ON breach_notifications(notification_deadline_date)
    WHERE status IN ('PENDING', 'DRAFTING', 'REVIEW');
```

---

## 15.11 SECURITY TESTING & VERIFICATION

### A. Penetration Testing Schedule

| Test Type | Frequency | Scope | Provider |
|-----------|-----------|-------|----------|
| External penetration test | Annual | Public-facing API, web app, mobile app | Third-party firm (NCC Group, Bishop Fox, or equivalent) |
| Internal penetration test | Annual | VPC internals, service-to-service, database | Third-party firm |
| Red team exercise | Annual | Social engineering + technical (full scope) | Third-party firm |
| Automated scanning | Continuous | OWASP ZAP, Nuclei — CI/CD integrated | Internal (automated) |
| Bug bounty program | Ongoing | Public-facing surfaces | HackerOne or Bugcrowd (launch at Phase 8) |

### B. Dependency Scanning

| Tool | Scope | Integration | Action on Critical CVE |
|------|-------|-------------|----------------------|
| **Dependabot** | Python (pip), JavaScript (npm) | GitHub Actions — auto-PR on vulnerability | Block deploy; patch within 24 hours |
| **Snyk** | Full dependency tree + container images | CI/CD pipeline + IDE plugin | Block merge; alert engineering |
| **ECR image scanning** | Docker images | On push to ECR | Block deployment if critical CVE |
| **pip-audit** | Python dependencies | Pre-commit hook + CI | Block commit if known vulnerability |
| **npm audit** | JavaScript dependencies | Pre-commit hook + CI | Block commit if known vulnerability |

### C. OWASP Top 10 Coverage

| OWASP Risk | Ciphergy Controls |
|------------|-------------------|
| **A01: Broken Access Control** | RLS on every table, JWT-scoped tenant isolation, RBAC, middleware enforcement chain |
| **A02: Cryptographic Failures** | AES-256-GCM for T4 data, TLS 1.3 everywhere, per-tenant KMS, no custom crypto |
| **A03: Injection** | Parameterized queries (SQLAlchemy ORM), input validation (Pydantic models), WAF SQL injection rules |
| **A04: Insecure Design** | Threat modeling in Phase 0, security architecture review, defense in depth |
| **A05: Security Misconfiguration** | AWS Config rules, infrastructure as code (Terraform), no default credentials, security headers |
| **A06: Vulnerable Components** | Dependabot + Snyk + pip-audit + npm audit, automated scanning in CI/CD |
| **A07: Authentication Failures** | MFA support, bcrypt password hashing, rate-limited auth endpoints, JWT with RS256 |
| **A08: Software and Data Integrity** | Signed container images, verified dependencies, CI/CD pipeline integrity |
| **A09: Security Logging Failures** | Comprehensive audit logging, CloudTrail, PII audit log, immutable security logs |
| **A10: Server-Side Request Forgery** | URL validation on MCP server calls, allowlist for external API endpoints, no user-controlled URLs |

### D. Agent-Specific Security Tests

AI agents introduce unique attack surfaces beyond traditional web application security. These tests are specific to Ciphergy's multi-agent architecture.

| Test Category | Test Description | Pass Criteria |
|---------------|-----------------|--------------|
| **Prompt Injection (Direct)** | Inject malicious instructions in user input attempting to override agent system prompts | Agent ignores injected instructions; system prompt takes precedence; attempt logged |
| **Prompt Injection (Indirect)** | Upload a document containing hidden instructions (invisible text, metadata) | PII pipeline detects anomalous content; agent does not execute injected instructions |
| **Jailbreak Detection** | Attempt to make agents produce content violating their role boundaries (e.g., Research Counsel drafting instead of researching) | Agent refuses out-of-role tasks; routes to correct agent; attempt logged |
| **Data Exfiltration via Agent** | Craft prompts that attempt to extract other tenants' data via agent responses | RLS prevents cross-tenant data access; agent cannot bypass database isolation |
| **PII Leakage in Output** | Provide T4 data and verify it does not appear in agent responses, logs, or telemetry | Stage 4 output filtering catches all PII; no T4 data in logs |
| **Token Exhaustion Attack** | Submit requests designed to maximize token consumption and exhaust tenant budget | Layer 4 agent loop protection triggers; circuit breaker activates; request terminated |
| **Citation Injection** | Provide fabricated citations and verify the anti-hallucination pipeline catches them | Research Counsel's 5-step verification flags fabricated citations as `[UNVERIFIED]` |
| **Privilege Escalation via WDC** | Attempt to manipulate WDC scoring to bypass Compliance veto | Compliance veto is architecturally enforced; cannot be overridden by score manipulation |
| **Cross-Agent Data Leakage** | Verify that private scratchpad data from one agent does not leak to other agents | Scratchpad isolation confirmed; only final outputs enter shared blackboard |
| **System Prompt Extraction** | Attempt to extract agent system prompts via crafted queries | System prompts are not included in user-facing responses; extraction attempts logged |

### E. Security Test Matrix

```
SECURITY TEST COVERAGE MATRIX

                    Unit    Integration  Pen Test  Automated  Agent-Specific
                    ─────   ───────────  ────────  ─────────  ──────────────
Authentication       [x]       [x]         [x]       [x]          ---
Authorization        [x]       [x]         [x]       [x]          [x]
Encryption           [x]       [x]         [x]       [x]          ---
Input Validation     [x]       [x]         [x]       [x]          [x]
PII Handling         [x]       [x]         [x]       [x]          [x]
Tenant Isolation     [x]       [x]         [x]       [x]          [x]
Rate Limiting        [x]       [x]         [x]       [x]          [x]
Prompt Injection     ---       ---         [x]       [x]          [x]
Session Management   [x]       [x]         [x]       [x]          ---
Error Handling       [x]       [x]         [x]       [x]          [x]
Logging Security     [x]       [x]         [x]       [x]          [x]
API Security         [x]       [x]         [x]       [x]          ---
Agent Boundaries     ---       [x]         ---       ---          [x]
WDC Integrity        ---       [x]         ---       ---          [x]

[x] = Covered by this test type
--- = Not applicable to this test type
```

### F. Continuous Security Monitoring

| Monitor | Tool | Alert Threshold | Response |
|---------|------|----------------|----------|
| Failed login attempts | CloudWatch + custom metric | >10 per user per hour | Lock account; notify user |
| RLS bypass attempts | Postgres audit extension | Any occurrence | P1 incident; immediate investigation |
| Anomalous API patterns | CloudWatch Anomaly Detection | 3-sigma deviation | Alert on-call; review logs |
| Certificate expiry | AWS Config | 14 days before expiry | Auto-renew (ACM); alert if manual |
| KMS key usage anomaly | CloudTrail + CloudWatch | Unusual decrypt volume | Alert security team; review access |
| Dependency vulnerability | Dependabot/Snyk | Critical or High CVE | Block deploy; patch within 24 hours |
| WAF block rate | Cloudflare dashboard | >1000 blocks per hour | Review attack pattern; adjust rules |
| Data egress anomaly | VPC Flow Logs | Unusual outbound volume | Alert on-call; review destination |

---

## 15.12 SECTION SUMMARY

| Layer | What It Protects | How | Section |
|-------|-----------------|-----|---------|
| **Data Classification** | All data — ensures appropriate controls per sensitivity | 4-tier framework with automatic classification | 15.1 |
| **Encryption** | Data in transit and at rest — prevents unauthorized reading | TLS 1.3 + AES-256 + per-tenant KMS | 15.2 |
| **PII Scrubbing** | Personal data — prevents exposure to agents and logs | 5-stage pipeline: scan, tag, redact, filter, audit | 15.3 |
| **Tenant Isolation** | Cross-tenant data — prevents one user seeing another's data | RLS + S3 policies + JWT scoping + VPC isolation | 15.4 |
| **LLM Data Handling** | Data sent to AI providers — prevents training and retention | Zero-retention, BAA, redacted context, VPC deployment option | 15.5 |
| **Compliance** | Regulatory obligations — prevents legal liability | HIPAA, GDPR, CCPA, SOC 2, state breach notification | 15.6 |
| **Data Lifecycle** | Data retention and deletion — prevents stale data and enables user rights | 7-year retention, cryptographic deletion, export | 15.7 |
| **Incident Response** | Breach handling — ensures rapid, compliant response | 4-severity classification, per-state notification, ERROR_MUSEUM | 15.8 |
| **Infrastructure** | Network and compute — prevents unauthorized access | VPC, WAF, DDoS protection, container security, secrets management | 15.9 |
| **Security Schemas** | Audit and tracking data — enables forensic capability | 5 SQL schemas for keys, PII audit, incidents, retention, breach notification | 15.10 |
| **Security Testing** | Continuous verification — prevents regression and novel attacks | Pen testing, dependency scanning, OWASP Top 10, agent-specific tests | 15.11 |

**The security posture:**
1. Data is classified by sensitivity and handled accordingly — automatically, not by policy alone
2. Every field that could identify a person is encrypted with keys the user effectively owns
3. Agents never see raw PII unless they absolutely need it for their specific task
4. No tenant can access another tenant's data, even if every application-level control fails — the database enforces it
5. The LLM provider cannot train on user data, retains it minimally, and the Enterprise tier eliminates data egress entirely
6. When something goes wrong, the incident response plan tells us exactly what to do, when, and who to notify
7. Every security control is tested — not just at launch, but continuously

---

**CONFIDENTIAL -- Bo Pennington / Pentek Design Build LLC**

*Section 15 addresses WDC-V2-SPEC-REVIEW Gap 2 (CRITICAL). This framework ensures that Ciphergy handles case data with the same care a law firm would — because the data is just as sensitive, the obligations are just as real, and the consequences of failure are just as severe.*
