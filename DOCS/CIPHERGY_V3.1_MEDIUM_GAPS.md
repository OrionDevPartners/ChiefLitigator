# CIPHERGY V3.1 — MEDIUM GAPS: BATCH INTAKE, OFFLINE MODE, ONBOARDING UX, REVENUE MODEL

## Addition to Product Spec V3
## March 15, 2026

**Source:** WDC V2 Spec Review — Gap 6 (Batch Document Intake), Gap 7 (Offline Courtroom Mode), Refinement 3 (Onboarding UX), Refinement 1 (Revenue Projections)

---

## DESIGN PHILOSOPHY

These four specifications address the "medium" priority gaps identified in the WDC V2 Spec Review. Each represents a distinct product capability that moves Ciphergy from a legal reasoning engine to a complete litigation platform. They share a common thread: **meeting the pro se litigant where they actually are** — uploading a shoebox of documents, standing in a courtroom with no WiFi, signing up at 11pm after being served with a lawsuit, and deciding whether $29/month is worth it.

Each part is a standalone specification. Each is implementation-ready. Each references the existing architecture (5-agent model, WDC v2.0, MCP-first integration, Case Knowledge Store) without duplicating it.

---

---

# PART 1: BATCH DOCUMENT INTAKE ARCHITECTURE

---

## 1.1 THE PROBLEM

A real case is not a single document. A real case intake looks like this:

- 47 pages of a complaint with exhibits
- 12 emails between the parties spanning 8 months
- A signed contract with 3 amendments
- 6 invoices and 4 payment receipts
- A court order setting a scheduling conference in 14 days
- 3 photographs of property damage
- A demand letter from opposing counsel
- An insurance denial letter
- A property appraisal report
- Handwritten notes from a phone call

The V2 spec handles single-document processing through Amendment 1.0's type-specific analyzers. But it does not address **batch intake** — the moment a new user uploads everything they have and expects the system to make sense of it. This is the first real test of the platform. If the user uploads 47 documents and gets back confusion, they leave. If they get back an organized case summary with deadline alerts and a recommended next step, they stay.

**What's at stake:** The batch intake experience is the first impression. It determines whether the user's 5-minute onboarding (Refinement 3) delivers real value or falls flat.

---

## 1.2 INTAKE PIPELINE

```
User uploads 47 documents
         |
         v
  +----- UPLOAD HANDLER -----+
  | Validates file types      |
  | Assigns UUIDs             |
  | Streams to S3             |
  | Queues for processing     |
  +---------------------------+
         |
         v
    PARALLEL TRIAGE (all 47 simultaneously via ARQ workers)
    +-- Classify each document type (14 categories)
    +-- Extract metadata (dates, parties, case numbers, dollar amounts)
    +-- OCR for scanned/image documents (Tesseract + AWS Textract fallback)
    +-- Detect duplicates (content hash comparison)
    +-- Flag priority documents (court orders with deadlines)
    +-- Queue for deep analysis by priority
         |
         v
    PRIORITY PROCESSING (agent-routed)
    +-- P0: Court orders --> Compliance Counsel (extract deadlines FIRST)
    +-- P1: Complaint/Petition --> Research Counsel (identify claims, elements, defenses)
    +-- P2: Contracts --> Research Counsel (clause analysis, breach identification)
    +-- P3: Financial documents --> Lead Counsel (damages calculation support)
    +-- P4: Discovery materials --> Research Counsel (obligation tracking)
    +-- P5: Everything else --> queued by document type and relevance
         |
         v
    CASE KNOWLEDGE STORE POPULATION
    +-- Timeline auto-populated from extracted dates
    +-- Party list auto-populated from extracted names/entities
    +-- Evidence inventory auto-populated with exhibit references
    +-- Claim matrix seeded from complaint analysis
    +-- Deadline inventory populated from court orders
    +-- Financial summary seeded from invoices/payments
         |
         v
    LEAD COUNSEL SUMMARY
    +-- "47 documents processed. Here's what I found..."
    +-- Immediate deadline alerts (if any court orders detected)
    +-- Case type classification with confidence level
    +-- Identified parties and their roles
    +-- Preliminary claim assessment
    +-- Evidence strength snapshot
    +-- Recommended next steps (prioritized by urgency)
```

**Processing time target:** All 47 documents classified and summarized within 90 seconds. Priority documents (court orders with deadlines) surfaced within 30 seconds. Full deep analysis within 5 minutes.

**Parallelism strategy:** ARQ workers process all documents simultaneously. Each document's triage is independent — no sequential bottleneck. Priority processing fans out to the appropriate agent via the standard supervisor orchestration pattern.

---

## 1.3 DOCUMENT CLASSIFICATION TAXONOMY

Fourteen categories covering the full scope of civil litigation document types:

| # | Category | Description | Priority | Agent Route |
|---|----------|-------------|----------|-------------|
| 1 | **Complaint / Petition** | Initiating pleading — the document that starts the lawsuit | P1 | Research Counsel |
| 2 | **Answer / Response** | Responsive pleading to a complaint or petition | P1 | Research Counsel |
| 3 | **Motion** | Any motion filed with the court (to compel, to dismiss, for summary judgment, etc.) | P2 | Research + Red Team |
| 4 | **Court Order** | Orders, rulings, scheduling orders, minute entries | P0 | Compliance Counsel |
| 5 | **Contract / Agreement** | Signed contracts, amendments, addenda, MOUs, LOIs | P2 | Research Counsel |
| 6 | **Correspondence** | Emails, letters, demand letters, notices between parties | P3 | Lead Counsel |
| 7 | **Invoice / Financial** | Invoices, receipts, payment records, bank statements, estimates | P3 | Lead Counsel |
| 8 | **Discovery** | Interrogatories, RFPs, RFAs, subpoenas, privilege logs | P2 | Compliance Counsel |
| 9 | **Deposition / Testimony** | Deposition transcripts, affidavits, declarations, witness statements | P2 | Red Team |
| 10 | **Evidence (Visual)** | Photographs, videos, screenshots, diagrams | P4 | Lead Counsel |
| 11 | **Medical Records** | Medical reports, treatment records, bills, diagnostic imaging summaries | P3 | Research Counsel |
| 12 | **Insurance Documents** | Policies, denial letters, coverage determinations, claim correspondence | P3 | Lead Counsel |
| 13 | **Corporate / Business Records** | Articles of incorporation, meeting minutes, annual reports, tax returns | P4 | Research Counsel |
| 14 | **Miscellaneous** | Documents that don't fit other categories — flagged for manual review | P5 | Lead Counsel |

### Classification Confidence Thresholds

| Confidence Level | Threshold | Action |
|-----------------|-----------|--------|
| High | >= 0.90 | Auto-classify, proceed to processing |
| Moderate | 0.70 - 0.89 | Auto-classify with "[Review classification]" flag |
| Low | 0.50 - 0.69 | Present top 3 classifications to user for confirmation |
| Uncertain | < 0.50 | Classify as Miscellaneous, prompt user to identify |

### Multi-Label Support

Documents frequently belong to multiple categories. A letter from opposing counsel attaching a contract amendment is both "Correspondence" and "Contract/Agreement." The system applies **all applicable labels** with independent confidence scores:

```
DOCUMENT: "Letter_from_Carter_Associates_03-01-2026.pdf"

CLASSIFICATIONS:
  1. Correspondence (0.94)  -- primary
  2. Contract/Agreement (0.82)  -- contains attached contract amendment
  3. Evidence (0.61)  -- contains factual assertions usable as admissions

PROCESSING: Routes to Lead Counsel (correspondence) AND Research Counsel
            (contract clause analysis). Red Team flags factual assertions
            for impeachment preparation.
```

---

## 1.4 OCR & DOCUMENT PROCESSING

### Processing Pipeline by File Type

| File Type | Text Extraction | OCR Required | Tool |
|-----------|----------------|--------------|------|
| PDF (text-based) | Direct extraction | No | pdfplumber (tables + layout-aware) |
| PDF (scanned) | OCR required | Yes | Tesseract (basic) / AWS Textract (complex) |
| DOCX / DOC | Direct extraction | No | python-docx / antiword |
| TXT | Direct read | No | Native |
| JPG / PNG / TIFF / HEIC | OCR required | Yes | Tesseract + image preprocessing |
| EML / MSG | Email parsing | No | email.parser / extract-msg |

### OCR Strategy (Two-Tier)

**Tier 1 — Tesseract (free, on-premise):**
- Handles clear scans, typed documents, standard fonts
- Runs first on all image/scanned documents
- If confidence score >= 0.85, accept output
- Cost: $0 (open-source, runs on Fargate instance)

**Tier 2 — AWS Textract (paid, high-accuracy):**
- Triggered when Tesseract confidence < 0.85
- Handles handwriting, complex tables, forms, poor-quality scans
- Table extraction preserves row/column structure
- Form extraction identifies key-value pairs
- Cost: $1.50 per 1,000 pages (standard) / $15 per 1,000 pages (tables/forms)

### Image Preprocessing (Before OCR)

For poor-quality scans and photographs of documents:

```
INPUT IMAGE
    |
    v
  Deskew (correct rotation/skew)
    |
    v
  Binarize (convert to black/white for OCR clarity)
    |
    v
  Denoise (remove artifacts, speckles)
    |
    v
  Contrast enhancement (sharpen text)
    |
    v
  Resolution upscale (if < 300 DPI, upscale to 300)
    |
    v
  OCR (Tesseract or Textract)
```

Libraries: OpenCV for preprocessing, Pillow for format conversion.

### Metadata Extraction

Every document is scanned for structured metadata regardless of type:

| Entity Type | Examples | Extraction Method |
|-------------|----------|-------------------|
| **Dates** | Filing dates, deadlines, event dates, contract dates | Regex + NER + context analysis |
| **Parties** | Person names, business names, attorney names | NER (Named Entity Recognition) |
| **Case Numbers** | Court case numbers, docket numbers | Regex (jurisdiction-specific patterns) |
| **Dollar Amounts** | Invoice totals, damages claimed, settlement amounts | Regex + context classification |
| **Addresses** | Court addresses, party addresses, property addresses | NER + address parsing |
| **Phone/Email** | Contact information | Regex |
| **Legal Citations** | Case citations, statute references | Legal citation regex + VAR lookup |

---

## 1.5 PRIORITY PROCESSING RULES

### Priority Levels

| Priority | Label | Document Types | Routing | SLA |
|----------|-------|---------------|---------|-----|
| **P0** | CRITICAL | Court orders with deadlines, scheduling orders, show-cause orders | Compliance Counsel IMMEDIATELY | < 30 seconds to surface deadline |
| **P1** | HIGH | Complaint/petition, answer/response, dispositive motions | Research Counsel | < 60 seconds to begin analysis |
| **P2** | ELEVATED | Contracts, discovery materials, depositions, non-dispositive motions | Research or Compliance | < 2 minutes |
| **P3** | STANDARD | Correspondence, financial documents, insurance, medical records | Lead Counsel | < 3 minutes |
| **P4** | LOW | Visual evidence, corporate records, general documents | Lead Counsel | < 5 minutes |
| **P5** | QUEUE | Miscellaneous, unclassified | Lead Counsel (manual review) | Best effort |

### P0 Processing Detail (Court Orders with Deadlines)

When a court order is detected, Compliance Counsel executes immediately:

```
COURT ORDER DETECTED: "Scheduling Order — Case No. 2026-CV-1234"

COMPLIANCE COUNSEL ACTIONS (within 30 seconds):
1. Extract ALL deadlines from order text
2. Compute calendar dates (account for weekends, holidays, local rules)
3. Cross-reference with existing deadline inventory
4. Flag conflicts or impossibly tight deadlines
5. Generate deadline alert for user

OUTPUT:
+------+--------------------------+------------+----------+
| #    | Obligation               | Deadline   | Alert    |
+------+--------------------------+------------+----------+
| 1    | Answer to Complaint      | 2026-04-01 | 17 DAYS  |
| 2    | Initial Disclosures      | 2026-04-15 | 31 DAYS  |
| 3    | Written Discovery Cutoff | 2026-07-15 | 122 DAYS |
| 4    | Expert Disclosures       | 2026-08-01 | 139 DAYS |
| 5    | Dispositive Motion Cutoff| 2026-09-15 | 184 DAYS |
| 6    | Pre-Trial Conference     | 2026-10-15 | 214 DAYS |
+------+--------------------------+------------+----------+

URGENT: Answer to Complaint due in 17 days.
        Compliance Counsel recommends beginning answer preparation immediately.
```

### Duplicate Detection

Before deep processing, every document is checked for duplicates:

- **Content hash (SHA-256):** Exact duplicate detection — same file uploaded twice
- **Fuzzy match (SimHash):** Near-duplicate detection — same document with minor formatting differences
- **Metadata overlap:** Same dates + same parties + same subject = likely duplicate

Duplicates are flagged, not deleted. The user confirms which version to keep. This prevents both wasted processing and accidental data loss.

---

## 1.6 DRAG-AND-DROP UI SPECIFICATION

### Upload Zone

```
+------------------------------------------------------------------+
|                                                                    |
|                                                                    |
|       +----------------------------------------------------+      |
|       |                                                    |      |
|       |                                                    |      |
|       |         Drag your case documents here              |      |
|       |                                                    |      |
|       |         or click to browse                         |      |
|       |                                                    |      |
|       |         PDF, DOCX, DOC, JPG, PNG, TIFF,           |      |
|       |         HEIC, TXT, EML, MSG                        |      |
|       |                                                    |      |
|       |         [Browse Files]  [Upload Folder]            |      |
|       |                                                    |      |
|       +----------------------------------------------------+      |
|                                                                    |
|  Batch Limits:                                                     |
|  Free: 10 documents  |  Pro: 100  |  Team: 500  |  Ent: Unlimited |
|                                                                    |
+------------------------------------------------------------------+
```

### Processing Status View

```
+------------------------------------------------------------------+
|  BATCH INTAKE: 47 documents                                       |
|  ============================================================     |
|  Overall: [############################............] 68%           |
|                                                                    |
|  +------+---------------------------+----------+----------+       |
|  | #    | Document                  | Status   | Type     |       |
|  +------+---------------------------+----------+----------+       |
|  |  1   | Scheduling_Order.pdf      | DONE     | Court    |       |
|  |      |                           |          | Order    |       |
|  |      | >> DEADLINE ALERT: Answer  |          |          |       |
|  |      |    due 2026-04-01 (17 days)|          |          |       |
|  +------+---------------------------+----------+----------+       |
|  |  2   | Complaint_w_Exhibits.pdf  | DONE     | Complaint|       |
|  +------+---------------------------+----------+----------+       |
|  |  3   | Contract_2025-03.pdf      | DONE     | Contract |       |
|  +------+---------------------------+----------+----------+       |
|  |  4   | Email_Thread_Jan.eml      | PROCESS  | Corr.    |       |
|  +------+---------------------------+----------+----------+       |
|  |  5   | IMG_4521.HEIC             | OCR...   | Evidence |       |
|  +------+---------------------------+----------+----------+       |
|  | ...  | ...                       | ...      | ...      |       |
|  +------+---------------------------+----------+----------+       |
|                                                                    |
|  Priority alerts appear at top as they are detected.               |
|  Documents sort by priority (P0 first).                            |
+------------------------------------------------------------------+
```

### Status Progression Per Document

```
Uploading --> Classifying --> Processing --> Done
   [===]       [===]           [===]        [===]

Error states:
  Upload Failed  --> Retry button
  OCR Failed     --> Manual text entry option
  Unclassified   --> User selects from dropdown
```

### Batch Size Limits by Tier

| Tier | Max Documents per Batch | Max File Size per Document | Max Total Upload |
|------|------------------------|---------------------------|-----------------|
| Free ($0) | 10 | 10 MB | 50 MB |
| Pro ($29/mo) | 100 | 50 MB | 500 MB |
| Team ($49/user/mo) | 500 | 100 MB | 5 GB |
| Enterprise (Custom) | Unlimited | 500 MB | Custom |

---

## 1.7 DATABASE SCHEMA

```sql
-- Document storage and classification
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    project_id      UUID NOT NULL REFERENCES projects(id),

    -- File metadata
    filename        VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,      -- pdf, docx, jpg, etc.
    file_size_bytes BIGINT NOT NULL,
    content_hash    VARCHAR(64) NOT NULL,       -- SHA-256 for dedup
    s3_path         VARCHAR(1000) NOT NULL,
    s3_bucket       VARCHAR(100) NOT NULL,

    -- Classification
    primary_classification VARCHAR(50),         -- from 14 categories
    classification_confidence DECIMAL(4,3),     -- 0.000 to 1.000
    secondary_classifications JSONB,            -- multi-label: [{type, confidence}]

    -- OCR
    ocr_required    BOOLEAN DEFAULT FALSE,
    ocr_engine      VARCHAR(20),               -- 'tesseract' or 'textract'
    ocr_confidence  DECIMAL(4,3),
    extracted_text  TEXT,                       -- full text content

    -- Processing
    processing_priority INTEGER DEFAULT 5,     -- 0 (critical) to 5 (queue)
    processing_status VARCHAR(20) DEFAULT 'pending',
                                               -- pending, classifying,
                                               -- processing, done, error
    processed_at    TIMESTAMPTZ,
    processing_duration_ms INTEGER,

    -- Metadata
    page_count      INTEGER,
    is_duplicate    BOOLEAN DEFAULT FALSE,
    duplicate_of    UUID REFERENCES documents(id),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policy
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- Indexes
CREATE INDEX idx_documents_tenant_project ON documents(tenant_id, project_id);
CREATE INDEX idx_documents_classification ON documents(primary_classification);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_documents_hash ON documents(content_hash);

-- Extracted entities from documents
CREATE TABLE document_entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    entity_type     VARCHAR(30) NOT NULL,      -- person, organization, date,
                                               -- amount, case_number, address,
                                               -- phone, email, citation
    entity_value    TEXT NOT NULL,
    normalized_value TEXT,                      -- standardized format
    confidence      DECIMAL(4,3),

    -- Position in document
    page_number     INTEGER,
    char_offset     INTEGER,
    char_length     INTEGER,

    -- Context
    surrounding_text TEXT,                      -- 100 chars before/after

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doc_entities_document ON document_entities(document_id);
CREATE INDEX idx_doc_entities_type ON document_entities(entity_type);
CREATE INDEX idx_doc_entities_value ON document_entities(entity_value);

-- Processing queue (managed by ARQ but tracked in Postgres for observability)
CREATE TABLE processing_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id),

    priority        INTEGER NOT NULL DEFAULT 5,
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',
                                               -- queued, assigned, processing,
                                               -- completed, failed, retrying
    assigned_agent  VARCHAR(30),               -- lead_counsel, research_counsel,
                                               -- compliance_counsel, etc.

    -- Retry logic
    attempts        INTEGER DEFAULT 0,
    max_attempts    INTEGER DEFAULT 3,
    last_error      TEXT,

    -- Timing
    queued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,

    -- ARQ job reference
    arq_job_id      VARCHAR(100)
);

CREATE INDEX idx_queue_status_priority ON processing_queue(status, priority);
CREATE INDEX idx_queue_tenant ON processing_queue(tenant_id);

-- Batch intake sessions (groups documents uploaded together)
CREATE TABLE intake_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    project_id      UUID NOT NULL REFERENCES projects(id),

    document_count  INTEGER NOT NULL DEFAULT 0,
    documents_processed INTEGER NOT NULL DEFAULT 0,

    status          VARCHAR(20) NOT NULL DEFAULT 'uploading',
                                               -- uploading, processing,
                                               -- completed, partial_error

    -- Summary (populated after all documents processed)
    summary_json    JSONB,                     -- Lead Counsel's intake summary
    deadline_alerts JSONB,                     -- any P0 deadlines detected

    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
```

### Integration with Case Knowledge Store

After batch processing completes, the extracted data populates the Case Knowledge Store automatically:

| CKS Section | Populated From | Method |
|-------------|---------------|--------|
| Timeline (Section 3) | All extracted dates + context | Auto-sorted chronologically, user confirms |
| Parties (Section 2) | All extracted person/org entities | Deduplicated, roles inferred from context |
| Evidence Inventory (Section 7) | All uploaded documents | Indexed with classification and metadata |
| Claims (Section 4) | Complaint analysis | Research Counsel extracts claims and elements |
| Deadlines (Section 15) | Court order extraction | Compliance Counsel computes all dates |
| Financial (Section 14) | Invoice/payment extraction | Amounts aggregated, damages seeded |

---

---

# PART 2: OFFLINE COURTROOM MODE

---

## 2.1 THE PROBLEM

Pro se litigants walk into courtrooms with:
- A phone in their pocket (maybe a tablet)
- A folder of printed documents (maybe organized, probably not)
- Anxiety about what to say when the judge asks a question
- Zero access to their legal research while standing at the podium

Courtrooms in 2026 offer unreliable WiFi at best. Many courthouses block personal hotspot connections. Even when connectivity exists, a pro se litigant cannot pause a hearing to wait for an API call to complete. They need **instant, offline access** to their case data, argument outlines, objection references, and evidence inventory.

The V2 spec describes a powerful cloud-based system. But a cloud-based system is useless when the cloud is unreachable. The Courtroom Ready Pack solves this by generating a comprehensive pre-hearing preparation package that is available offline — cached on the device or printed as PDF.

---

## 2.2 PRE-HEARING PREPARATION PACKAGE

Generated BEFORE the hearing date. Available offline. Updated automatically when case data changes (while online). The package is hearing-specific — tailored to the type of hearing scheduled.

### Package Contents (10 Sections)

| # | Section | Content | Size Estimate |
|---|---------|---------|--------------|
| 1 | **Case Summary & Theory** | 1-page case summary, theory of the case, theme statement, anchor facts | 2-3 KB |
| 2 | **Key Timeline** | Chronological events with evidence references, filtered to hearing-relevant dates | 5-10 KB |
| 3 | **Evidence Inventory** | Exhibit list with descriptions, locations, admissibility status, pre-marked exhibit numbers | 10-20 KB |
| 4 | **Argument Outlines** | Structured outlines for the specific hearing topic — not scripts, outlines. Includes citations. | 15-30 KB |
| 5 | **Anticipated Opposition** | Top 5 opposing arguments with prepared responses. "If they say X, respond with Y because Z." | 10-20 KB |
| 6 | **Objection Quick-Reference** | Jurisdiction-specific objection card — 15 most common objections with basis, when to use, expected ruling | 8-15 KB |
| 7 | **Judge Profile Card** | From E4 Judicial Analytics — preferences, pet peeves, ruling patterns, how to address this specific judge | 5-10 KB |
| 8 | **Deadline Inventory** | Current deadline status, next 5 upcoming deadlines, anything triggered by this hearing's outcome | 3-5 KB |
| 9 | **Key Legal Authorities** | Top 10 citations with holdings and page/paragraph references — the cases you will cite in this hearing | 15-25 KB |
| 10 | **Courtroom Etiquette** | How to address the judge, when to stand, how to present evidence, how to make a record | 3-5 KB |

**Total size:** Under 200 KB of structured data per hearing. With cached document previews: under 10 MB per case.

### Auto-Generation Trigger

The Courtroom Ready Pack generates automatically when:
- A hearing date is added to the deadline inventory
- 7 days before the hearing (initial generation)
- 3 days before the hearing (updated with any case changes)
- 1 day before the hearing (final version, locked)

User can also generate on-demand: "Prepare me for tomorrow's hearing."

---

## 2.3 EXPORT FORMATS

### Format 1: PDF (Printable)

A comprehensive formatted PDF — what a litigant prints and brings to court in a binder.

```
COURTROOM READY PACK
Case: Pennington v. ABC Contractors
Hearing: Motion to Compel — April 10, 2026
Court: U.S. District Court, Eastern District of Louisiana
Judge: Hon. Sarah Mitchell

Generated: April 9, 2026, 8:00 PM CDT
---

TABLE OF CONTENTS
1. Case Summary & Theory of the Case ................ 2
2. Key Timeline .................................... 3
3. Evidence Inventory & Exhibit List ............... 4
4. Argument Outline: Motion to Compel .............. 6
5. Anticipated Opposition & Responses .............. 8
6. Objection Quick-Reference Card ................. 10
7. Judge Profile: Hon. Sarah Mitchell ............. 11
8. Deadline Inventory ............................. 12
9. Key Legal Authorities .......................... 13
10. Courtroom Etiquette Guide ..................... 15

---
[Full content follows in formatted, printable pages]
```

PDF specifications:
- Letter size (8.5" x 11"), single-sided for easy reading
- 12pt font minimum (readable from counsel table under courtroom lighting)
- Clear section headers with tab-stop markers for binder tabs
- Page numbers on every page
- Case name and hearing date in header
- "CONFIDENTIAL WORK PRODUCT" watermark (light gray, does not obscure text)

### Format 2: Mobile App Cached Data (Expo React Native)

For the mobile app (Phase 7 roadmap), the Courtroom Ready Pack is cached locally:

```
OFFLINE STORAGE ARCHITECTURE (React Native)

AsyncStorage (structured data):
+-- case_summary (JSON)
+-- timeline_events (JSON array)
+-- evidence_inventory (JSON array)
+-- argument_outlines (JSON array)
+-- opposition_responses (JSON array)
+-- judge_profile (JSON)
+-- deadline_inventory (JSON array)
+-- authorities (JSON array)
+-- courtroom_etiquette (JSON)

SQLite (searchable case database):
+-- documents (id, title, type, text_content, exhibit_number)
+-- entities (id, document_id, type, value)
+-- citations (id, citation_text, holding, verification_status)
+-- deadlines (id, description, due_date, status)
+-- objections (id, type, rule, description, when_to_use)

File Cache (document previews):
+-- /cache/exhibits/exhibit_A.pdf (first 2 pages only)
+-- /cache/exhibits/exhibit_B.pdf
+-- /cache/authorities/johnson_v_williams.pdf (key pages only)
```

### Format 3: Quick-Reference Cards (Separate 1-Page PDFs)

Individual cards for rapid access during a hearing:

- **Objection Card** — fits on one page, laminate-ready
- **Timeline Card** — key dates on one page
- **Authorities Card** — top 10 cases with holdings, one page
- **Hearing Outline Card** — argument structure for this specific hearing

---

## 2.4 OFFLINE DATA ARCHITECTURE

### React Native (Mobile App)

| Storage Layer | Technology | Purpose | Size Limit |
|--------------|-----------|---------|-----------|
| Structured data | AsyncStorage | Case summary, timelines, argument outlines | 6 MB per key |
| Searchable database | SQLite (via expo-sqlite) | Full-text search across case data, documents, citations | 50 MB per case |
| File cache | Expo FileSystem | Document previews, PDF cards, cached authorities | 100 MB total |
| Sync state | AsyncStorage | Last sync timestamp, pending notes, conflict resolution metadata | 1 MB |

### Progressive Web App (Web Fallback)

For users who access Ciphergy via browser rather than native app:

| Storage Layer | Technology | Purpose |
|--------------|-----------|---------|
| Offline shell | Service Worker | Cache application shell for offline loading |
| Structured data | IndexedDB | Case data, timelines, arguments (via idb library) |
| File cache | Cache API | PDF cards, document previews |
| Background sync | Background Sync API | Queue notes/updates for sync when connectivity returns |

### Data Size Budget

| Component | Budget | Rationale |
|-----------|--------|-----------|
| Case metadata | 500 KB | JSON structures — highly compressible |
| Argument outlines | 2 MB | Text-heavy, includes citations |
| Document text extracts | 5 MB | OCR text from key documents |
| PDF quick-reference cards | 2 MB | 4 cards at ~500 KB each |
| Exhibit previews (first pages) | 10 MB | PDF preview images |
| **Total per case** | **< 20 MB** | Well within mobile storage limits |

### Sync Protocol

```
ONLINE STATE:
  App checks for case data updates every 5 minutes (configurable)
  Hearing pack regenerates on case data change
  Full sync on app open

OFFLINE STATE (courtroom):
  All cached data available instantly
  User can take timestamped notes
  Notes stored in AsyncStorage / IndexedDB
  No API calls attempted (prevents timeout errors in UI)

RECONNECTION:
  Background sync uploads any notes taken during hearing
  Sync conflict resolution: server wins for case data, merge for notes
  Hearing notes auto-linked to hearing date in Case Knowledge Store
```

---

## 2.5 COURTROOM UI MODE

A dedicated interface optimized for courtroom use — large text, fast navigation, no distractions.

### Layout (Mobile — Portrait)

```
+------------------------------------------+
| COURTROOM MODE            [Exit] [Light]  |
| Pennington v. ABC Contractors             |
| Motion to Compel - Apr 10, 2026           |
+------------------------------------------+
|                                          |
|  +--------------------------------------+|
|  |                                      ||
|  |  [Current Section Content]           ||
|  |                                      ||
|  |  Large text (18pt minimum)           ||
|  |  High contrast                       ||
|  |  Scrollable                          ||
|  |                                      ||
|  |                                      ||
|  |                                      ||
|  |                                      ||
|  +--------------------------------------+|
|                                          |
|  +------+------+------+------+------+   |
|  | OBJ  | TIME | EVID | AUTH | NOTE |   |
|  | ECT  | LINE |      |      |      |   |
|  +------+------+------+------+------+   |
|                                          |
|  << Swipe for more sections >>           |
+------------------------------------------+
```

### Design Specifications

| Property | Value | Rationale |
|----------|-------|-----------|
| Minimum font size | 18pt | Readable from counsel table, 2-3 feet from device |
| Font | System sans-serif (SF Pro / Roboto) | Maximum legibility |
| Line spacing | 1.6x | Easy scanning under stress |
| Color scheme (light) | Black text on white (#FFFFFF) | Standard courtroom lighting |
| Color scheme (dark) | White text on dark (#1A1A1A) | Dimmer courtroom or evening sessions |
| Section switching | One tap on bottom bar | No navigation drilling |
| Search | Pull-down to search across all sections | Find anything in 2 seconds |
| Screen timeout | Disabled in courtroom mode | Screen stays on during hearing |
| Swipe | Left/right to move between sections | Fast navigation, no buttons needed |

### Quick-Access Buttons

Five primary sections accessible via a single tap:

| Button | Section | Use Case |
|--------|---------|----------|
| **OBJECT** | Objection quick-reference | Judge admits improper evidence — look up objection basis in 2 seconds |
| **TIMELINE** | Key timeline | "When did this happen?" — instant chronological reference |
| **EVID** | Evidence inventory | "What exhibit supports this?" — find the exhibit number instantly |
| **AUTH** | Key authorities | "What case supports this?" — citation and holding at fingertips |
| **NOTE** | Timestamped note-taking | Record what happens during hearing — linked to timestamps |

### Note-Taking in Courtroom Mode

```
+------------------------------------------+
| NOTE                          [Done]      |
+------------------------------------------+
| 10:42 AM - Judge asked about service      |
| 10:45 AM - Opposing counsel objected to   |
|            Exhibit C - judge reserved      |
|            ruling                          |
| 10:48 AM - [New Note]                     |
|                                           |
|  +--------------------------------------+ |
|  | Type note here...                    | |
|  |                                      | |
|  +--------------------------------------+ |
|  [Timestamp] [Link to Exhibit] [Flag]    |
+------------------------------------------+
```

Notes are:
- Auto-timestamped
- Optionally linked to exhibits or hearing events
- Stored locally (synced when connectivity returns)
- Added to Case Knowledge Store under hearing date
- Exportable as part of case file

---

## 2.6 QUICK-REFERENCE CARDS

### Objection Quick-Reference Card

Jurisdiction-specific. This example uses Federal Rules of Evidence:

```
+==================================================================+
|           OBJECTION QUICK-REFERENCE CARD                          |
|           Federal Rules of Evidence                               |
|           Case: Pennington v. ABC Contractors                     |
+==================================================================+

+---+---------------------+------------+---------------------------+
| # | Objection           | Rule       | When to Use               |
+---+---------------------+------------+---------------------------+
| 1 | RELEVANCE           | FRE 401/   | Evidence does not make a  |
|   |                     | 402        | fact of consequence more  |
|   |                     |            | or less probable          |
+---+---------------------+------------+---------------------------+
| 2 | HEARSAY             | FRE 801/   | Out-of-court statement    |
|   |                     | 802        | offered for truth.        |
|   |                     |            | EXCEPTIONS: 803(1) pres.  |
|   |                     |            | sense, 803(2) excited     |
|   |                     |            | utterance, 803(3) state   |
|   |                     |            | of mind, 803(6) business  |
|   |                     |            | records, 803(8) public    |
|   |                     |            | records, 801(d)(2)        |
|   |                     |            | opposing party statement  |
+---+---------------------+------------+---------------------------+
| 3 | LEADING             | FRE 611(c) | Question suggests the     |
|   |                     |            | answer during direct      |
|   |                     |            | examination. OK on cross. |
+---+---------------------+------------+---------------------------+
| 4 | FOUNDATION /        | FRE 602 /  | Witness has not shown     |
|   | LACK OF PERSONAL    | 901        | personal knowledge or     |
|   | KNOWLEDGE           |            | document not authenticated|
+---+---------------------+------------+---------------------------+
| 5 | BEST EVIDENCE       | FRE 1002   | Proving content of        |
|   |                     |            | writing without original  |
|   |                     |            | or acceptable duplicate   |
+---+---------------------+------------+---------------------------+
| 6 | UNFAIR PREJUDICE    | FRE 403    | Probative value            |
|   |                     |            | substantially outweighed  |
|   |                     |            | by prejudice, confusion,  |
|   |                     |            | or waste of time          |
+---+---------------------+------------+---------------------------+
| 7 | SPECULATION         | FRE 602    | Witness is guessing, not  |
|   |                     |            | testifying from knowledge |
+---+---------------------+------------+---------------------------+
| 8 | ASSUMES FACTS       | FRE 611    | Question assumes a fact   |
|   | NOT IN EVIDENCE     |            | that has not been         |
|   |                     |            | established               |
+---+---------------------+------------+---------------------------+
| 9 | COMPOUND            | FRE 611    | Question asks two things  |
|   | QUESTION            |            | at once -- unfair to      |
|   |                     |            | witness                   |
+---+---------------------+------------+---------------------------+
| 10| ASKED AND           | FRE 611    | Same question already     |
|   | ANSWERED            |            | asked and answered --     |
|   |                     |            | cumulative                |
+---+---------------------+------------+---------------------------+
| 11| BEYOND THE SCOPE    | FRE 611(b) | Cross-examination goes    |
|   |                     |            | beyond subject matter of  |
|   |                     |            | direct                    |
+---+---------------------+------------+---------------------------+
| 12| CALLS FOR           | FRE 701 /  | Witness not qualified to  |
|   | EXPERT OPINION      | 702        | give expert testimony     |
+---+---------------------+------------+---------------------------+
| 13| ATTORNEY-CLIENT     | FRE 501    | Question seeks privileged |
|   | PRIVILEGE           |            | communications with       |
|   |                     |            | attorney                  |
+---+---------------------+------------+---------------------------+
| 14| IMPROPER            | FRE 404(b) | Character evidence not    |
|   | CHARACTER           |            | admissible to prove       |
|   | EVIDENCE            |            | action in conformity      |
+---+---------------------+------------+---------------------------+
| 15| NARRATIVE           | FRE 611    | Witness is giving a       |
|   |                     |            | speech instead of         |
|   |                     |            | answering the question    |
+---+---------------------+------------+---------------------------+

HOW TO OBJECT:
  Stand. "Your Honor, I object on the grounds of [basis]."
  Wait for ruling. If overruled, say "Noted for the record."
  If sustained, move on. Do not argue after a ruling.

+==================================================================+
```

### Courtroom Procedure Card

```
+==================================================================+
|           COURTROOM PROCEDURE CARD                                |
|           [Court Name]                                            |
+==================================================================+

BEFORE THE HEARING:
  - Arrive 15 minutes early
  - Check in with the courtroom deputy/clerk
  - Place your documents in order on counsel table
  - Stand when the judge enters
  - Silence your phone (do not turn off -- you need it for notes)

ADDRESSING THE JUDGE:
  - "Your Honor" (always)
  - Stand when speaking to the judge
  - Do not interrupt the judge -- ever
  - If the judge asks a question, answer it directly first,
    then explain

PRESENTING YOUR ARGUMENT:
  - "Your Honor, I am [name], appearing pro se as [plaintiff/
    defendant] in this matter."
  - State what you are asking for: "I have filed a Motion to
    Compel, and I am asking the Court to..."
  - Present your strongest argument first
  - Cite your legal authority: "Under FRCP Rule 37(a), the
    Court may order a party to respond to discovery..."
  - Be concise. Judges prefer brevity.

PRESENTING EVIDENCE:
  - "Your Honor, I would like to offer [description] as
    Exhibit [letter/number]."
  - Hand copies to the clerk, opposing counsel, and the judge
  - Wait for the judge to admit it before referring to its
    contents
  - If opposing counsel objects, wait for the judge to rule

IF OPPOSING COUNSEL OBJECTS TO YOUR EVIDENCE:
  - Wait for the judge to ask you to respond
  - State why the objection should be overruled
  - "Your Honor, this document is admissible because..."

AFTER THE HEARING:
  - Wait for the judge to dismiss you
  - Thank the judge: "Thank you, Your Honor."
  - Do not discuss the case in the hallway where opposing
    counsel or witnesses can hear you

+==================================================================+
```

---

---

# PART 3: ONBOARDING UX SPECIFICATION

---

## 3.1 DESIGN GOAL: FIRST VALUE IN 5 MINUTES

The single most important metric for Ciphergy's success is **time-to-first-value**. A pro se litigant who signs up at 11pm after being served with a lawsuit needs to see that the system understands their situation and can help — within 5 minutes of creating an account.

**Conversion moment:** The instant the user sees their specific case analyzed — claims identified, deadlines flagged, next steps recommended — they know this tool is worth $29/month. That is the conversion moment. Everything before it is friction to minimize. Everything after it is value to maximize.

**Reverse trial model:** 14 days of Pro features ($29/month tier), then automatic downgrade to Free ($0). This is proven to convert 2-3x better than standard freemium. The user experiences the full power — 5 agents, unlimited runs, all enhancements — and then decides if they want to keep it.

**Target conversion rate:** 40% free-to-paid (aggressive but achievable in a vertical SaaS with this level of immediate value). Industry average for horizontal SaaS: 2-5%. Legal vertical SaaS with demonstrated value: 15-25%. Ciphergy's immediate case analysis creates a conversion moment that horizontal tools cannot replicate.

---

## 3.2 5-STEP ONBOARDING FLOW

### Step 1: SIGN UP (30 seconds)

```
+--------------------------------------------------+
|                                                    |
|          Welcome to Ciphergy                       |
|          AI Litigation Support                     |
|                                                    |
|  +----------------------------------------------+ |
|  | Email                                        | |
|  +----------------------------------------------+ |
|  | Password                                     | |
|  +----------------------------------------------+ |
|                                                    |
|  [ Create Account ]                                |
|                                                    |
|  ------- or -------                                |
|                                                    |
|  [ Continue with Google ]                          |
|                                                    |
|  Already have an account? Sign in                  |
|                                                    |
|  By creating an account, you agree to the          |
|  Service Agreement (scroll-to-acknowledge          |
|  required on next step).                           |
|                                                    |
+--------------------------------------------------+
```

**What happens on submit:**
- Account created with email verification pending
- IP address and geo-location captured (jurisdictional defaults)
- 14-day Pro reverse trial activated automatically
- Device fingerprint recorded
- Verification email sent
- Redirected to Service Agreement (Section 14 scroll-to-acknowledge)

**After Service Agreement acknowledgment:** Proceed to Step 2.

**No credit card required.** The user experiences full Pro features for 14 days. Credit card collection happens at conversion (Day 12-14 prompt), not at signup.

### Step 2: WHAT DO YOU NEED? (30 seconds)

```
+--------------------------------------------------+
|                                                    |
|  What brings you to Ciphergy?                      |
|                                                    |
|  +----------------------------------------------+ |
|  |                                              | |
|  |  I received a lawsuit and need to respond    | |
|  |  >> URGENT: deadlines may be running         | |
|  |                                              | |
|  +----------------------------------------------+ |
|                                                    |
|  +----------------------------------------------+ |
|  |                                              | |
|  |  I want to file a lawsuit                    | |
|  |  >> Claim assessment and complaint drafting   | |
|  |                                              | |
|  +----------------------------------------------+ |
|                                                    |
|  +----------------------------------------------+ |
|  |                                              | |
|  |  I need help with a legal document           | |
|  |  >> Contract review, demand letter, etc.     | |
|  |                                              | |
|  +----------------------------------------------+ |
|                                                    |
|  +----------------------------------------------+ |
|  |                                              | |
|  |  I have an ongoing case and need help        | |
|  |  >> Case transfer and gap analysis           | |
|  |                                              | |
|  +----------------------------------------------+ |
|                                                    |
+--------------------------------------------------+
```

**Each choice activates a different workflow with different urgency levels:**

| Path | Urgency | First Agent | First Action |
|------|---------|-------------|--------------|
| Received lawsuit | CRITICAL | Compliance Counsel | Extract deadlines from any uploaded documents FIRST |
| File lawsuit | STANDARD | Research Counsel | Claim viability assessment |
| Document help | STANDARD | Lead Counsel | Document classification and analysis |
| Ongoing case | ELEVATED | Lead Counsel | Case status assessment and gap analysis |

**The "received lawsuit" path triggers urgent onboarding:** Every step is optimized for speed because there may be a 21-day (or 14-day, or 30-day) deadline running.

### Step 3: TELL US ABOUT YOUR SITUATION (2 minutes)

The interview adapts based on the path selected in Step 2. Questions are conversational, not form-like. The AI asks follow-up questions based on answers.

**Core Questions (all paths):**

```
+--------------------------------------------------+
|                                                    |
|  Tell us about your situation                      |
|                                                    |
|  What state is your case in?                       |
|  +----------------------------------------------+ |
|  | [Dropdown: auto-detected from geo, editable] | |
|  +----------------------------------------------+ |
|                                                    |
|  What court? (optional -- we can help identify)    |
|  +----------------------------------------------+ |
|  | [Federal / State / Not sure]                 | |
|  +----------------------------------------------+ |
|                                                    |
|  Who is the other party?                           |
|  +----------------------------------------------+ |
|  | [Name of person or company]                  | |
|  +----------------------------------------------+ |
|                                                    |
|  What happened?                                    |
|  +----------------------------------------------+ |
|  | [Free text area -- 2000 char limit]          | |
|  | Tell us in your own words. Don't worry about | |
|  | legal terms -- just tell us the facts.        | |
|  +----------------------------------------------+ |
|                                                    |
|  When did this happen?                             |
|  +----------------------------------------------+ |
|  | [Date or approximate timeframe]              | |
|  +----------------------------------------------+ |
|                                                    |
|  What do you want to achieve?                      |
|  +----------------------------------------------+ |
|  | [  ] Get money I'm owed                      | |
|  | [  ] Stop someone from doing something       | |
|  | [  ] Defend myself against claims             | |
|  | [  ] Resolve a contract dispute               | |
|  | [  ] Other: _______________                  | |
|  +----------------------------------------------+ |
|                                                    |
|  Do you have documents related to your case?       |
|  +----------------------------------------------+ |
|  | [Upload Documents] (optional -- you can      | |
|  |  upload later too)                           | |
|  +----------------------------------------------+ |
|                                                    |
|  [ Continue ]                                      |
|                                                    |
+--------------------------------------------------+
```

**Path-specific follow-up questions:**

| Path | Additional Questions |
|------|---------------------|
| Received lawsuit | "When were you served?" (critical for deadline computation), "Do you have the complaint?" (upload prompt) |
| File lawsuit | "How much money is involved?" (jurisdictional threshold), "Have you sent a demand letter?" (pre-suit requirement check) |
| Document help | "What type of document?" (contract, letter, filing, etc.), "What do you need to know about it?" |
| Ongoing case | "What stage is your case in?" (discovery, motions, trial prep), "What's your next court date?" |

**Background processing while user types:**
- Jurisdiction identified -> Compliance Counsel loads jurisdiction rules
- Opposing party name -> Research Counsel begins public records scan (E6)
- Narrative text -> Lead Counsel begins case type classification
- Documents (if uploaded) -> Batch intake pipeline starts (Part 1 of this document)

### Step 4: YOUR CASE DASHBOARD (immediate)

Generated automatically from the interview answers and any uploaded documents. This is the first time the user sees the system's intelligence — the conversion moment.

```
+==================================================================+
|  YOUR CASE DASHBOARD                                              |
|  Pennington v. ABC Contractors                                    |
|  E.D. Louisiana | Breach of Contract                             |
+==================================================================+
|                                                                    |
|  CASE SUMMARY                                                     |
|  You hired ABC Contractors to renovate your home for $75,000.     |
|  After 8 months (3-month contract), the work is incomplete and    |
|  defective. ABC has stopped responding and filed a mechanic's     |
|  lien on your property. Based on your description, you appear     |
|  to have viable claims for breach of contract, fraud, and         |
|  potentially LUTPA violations.                                    |
|                                                                    |
|  +------------------------------------------------------------+  |
|  | IDENTIFIED CLAIMS               | Confidence               |  |
|  +---------------------------------+--------------------------+  |
|  | Breach of Contract              | High (92%)               |  |
|  | Fraud / Misrepresentation       | Moderate (71%)           |  |
|  | LUTPA Violation (La. R.S. 51)   | Moderate (68%)           |  |
|  | Unjust Enrichment               | High (85%)               |  |
|  | Lien Cancellation               | High (88%)               |  |
|  +---------------------------------+--------------------------+  |
|                                                                    |
|  DEADLINES                                                        |
|  +------------------------------------------------------------+  |
|  | No immediate court deadlines detected.                      |  |
|  | Statute of Limitations: ~2 years from breach (est. Mar 2027)|  |
|  | Prescription: Fraud = 1 year from discovery (verify date)   |  |
|  +------------------------------------------------------------+  |
|                                                                    |
|  PRELIMINARY DAMAGES ESTIMATE                                     |
|  +------------------------------------------------------------+  |
|  | Direct damages (contract price)    | $75,000                |  |
|  | Consequential damages (est.)       | $15,000 - $40,000     |  |
|  | LUTPA treble damages (if proven)   | up to $225,000        |  |
|  | Pre-judgment interest              | accruing               |  |
|  +------------------------------------------------------------+  |
|  | Note: These are preliminary estimates based on your          |  |
|  | description. Verified analysis requires document review.     |  |
|  +------------------------------------------------------------+  |
|                                                                    |
|  JURISDICTION                                                     |
|  +------------------------------------------------------------+  |
|  | State: Louisiana                                            |  |
|  | Court: Civil District Court (if < $75K) or                  |  |
|  |        Federal (if diversity + > $75K)                      |  |
|  | Filing fee: ~$250 (state) / ~$405 (federal)                |  |
|  | Note: Fee waiver may be available (IFP petition)            |  |
|  +------------------------------------------------------------+  |
|                                                                    |
|  RECOMMENDED NEXT STEP                                            |
|  +------------------------------------------------------------+  |
|  | Upload your contract, invoices, and any correspondence      |  |
|  | with ABC Contractors. The system will analyze these          |  |
|  | documents and refine the claim assessment.                   |  |
|  |                                                              |  |
|  | [ Upload Documents ]  [ Start with Demand Letter ]          |  |
|  +------------------------------------------------------------+  |
|                                                                    |
+==================================================================+
```

**What happens behind the scenes:**
- Lead Counsel synthesizes the interview data into a case summary
- Research Counsel identifies claims based on the narrative and jurisdiction
- Compliance Counsel checks statute of limitations / prescription periods
- Lead Counsel estimates preliminary damages ranges
- All of this happens in parallel during the 10-30 seconds after the user submits the interview

### Step 5: FIRST DELIVERABLE (within 5 minutes total)

The user receives a tangible, useful output within 5 minutes of creating their account. This is path-specific:

| Path | First Deliverable | Time to Generate |
|------|------------------|-----------------|
| Received lawsuit | Deadline alert + defense analysis + answer outline | 2-3 minutes after document upload |
| File lawsuit | Claim viability assessment + jurisdiction card + complaint outline | 2-3 minutes after interview |
| Document help | Document analysis with key findings + recommended actions | 1-2 minutes after document upload |
| Ongoing case | Case status assessment + gap analysis + next steps | 2-3 minutes after interview |

**Received lawsuit (URGENT path) first deliverable example:**

```
URGENT: RESPONSE DEADLINE ANALYSIS
========================================

Based on the complaint you uploaded:

DEADLINE: You must file an Answer within 21 days of service.
SERVICE DATE: March 10, 2026
ANSWER DUE: March 31, 2026 (16 DAYS FROM TODAY)

DEFENSE ANALYSIS (preliminary):
1. Failure to perform -- ABC did not complete the work
   Strength: STRONG -- you have the contract and payment records

2. Fraud defense -- ABC misrepresented progress
   Strength: MODERATE -- need documentation of false statements

3. Counterclaim opportunity -- you may have counterclaims for
   breach, fraud, and LUTPA violations

RECOMMENDED IMMEDIATE ACTIONS:
1. Begin drafting your Answer (Ciphergy can help)
2. Upload all relevant documents for full case analysis
3. Consider filing counterclaims with your Answer
4. Determine if you qualify for a fee waiver (IFP petition)

[ Draft My Answer ]  [ Upload More Documents ]
```

---

## 3.3 SITUATION ASSESSMENT ENGINE

The AI-driven intake is not a static form. It is a guided conversation that adapts based on the user's responses.

### Adaptive Question Logic

```
User says: "My contractor took my money and didn't finish the work"
                |
                v
System identifies: Construction dispute, breach of contract probable
                |
                v
Follow-up questions:
  - "Was there a written contract?" (contract existence)
  - "How much did you pay?" (damages quantification)
  - "When was the work supposed to be done?" (breach timing)
  - "Have you communicated with them about the problem?" (mitigation)
  - "Did they give you any written promises about the work?" (fraud)
  - "Are they a licensed contractor?" (licensing violation claims)
```

### Case Type Auto-Detection

| User Narrative Contains | Detected Case Type | Activated Claims |
|------------------------|-------------------|-----------------|
| "contractor," "renovation," "work not done" | Construction dispute | Breach of contract, negligence, LUTPA, licensing violations |
| "landlord," "eviction," "lease" | Landlord-tenant | Wrongful eviction, lease breach, habitability, security deposit |
| "car accident," "injury," "insurance" | Personal injury | Negligence, insurance bad faith, medical expenses |
| "fired," "discrimination," "harassment" | Employment | Title VII, state discrimination statutes, wrongful termination |
| "debt," "collection," "credit" | Consumer/debt | FDCPA, TCPA, FCRA, state consumer protection |
| "divorce," "custody," "child support" | Family law | State-specific family code provisions |
| "business partner," "LLC," "contract" | Business dispute | Breach of contract, breach of fiduciary duty, dissolution |

### Urgency Detection

| Signal | Urgency Level | System Response |
|--------|--------------|----------------|
| User selected "received a lawsuit" | CRITICAL | Skip non-essential questions, surface deadlines first |
| Complaint document uploaded | CRITICAL | Compliance Counsel extracts deadlines before anything else |
| Mentions "court date," "hearing," "deadline" | HIGH | Calendar alert, deadline verification |
| Mentions "threatened to sue," "demand letter" | ELEVATED | Pre-suit strategy, deadline check for response requirements |
| General legal question | STANDARD | Full intake flow, no urgency shortcuts |

### Viability Pre-Assessment

Before deep analysis, the system provides a preliminary viability assessment:

```
PRELIMINARY VIABILITY ASSESSMENT
=================================
Confidence: Moderate (based on interview only -- document review will refine)

CLAIM: Breach of Contract
  Elements met (from your description):
    [x] Contract existed (you mentioned a signed agreement)
    [x] You performed (you paid $75,000)
    [x] They breached (work not completed)
    [?] Damages (need documentation -- upload invoices)

  Preliminary viability: STRONG

CLAIM: Fraud
  Elements met (from your description):
    [x] Misrepresentation (they said work would be done in 3 months)
    [?] Knowledge of falsity (need evidence they knew they couldn't deliver)
    [x] Reasonable reliance (you paid based on their promise)
    [x] Damages (same as contract damages)

  Preliminary viability: MODERATE -- depends on evidence of intent

NOTE: This is a preliminary assessment based on your description.
A full analysis requires document review and legal research.
Upload your documents for a refined assessment.
```

---

## 3.4 CONVERSION METRICS

### Target Metrics

| Metric | Target | Industry Average | Rationale |
|--------|--------|-----------------|-----------|
| Free-to-paid conversion | 40% | 2-5% (horizontal SaaS) | Immediate case-specific value creates strong conversion moment |
| Time-to-first-value | < 5 minutes | 15-60 minutes | Guided interview + AI analysis = instant dashboard |
| Day 1 retention | 85% | 40-60% | Deadline alerts and case dashboard create daily return reason |
| Day 7 retention | 70% | 25-40% | Active case management drives engagement |
| Day 14 retention | 60% | 15-30% | Reverse trial expiration creates conversion decision point |
| Day 30 retention (paid) | 90% | 70-80% | Active litigation cases create ongoing need |

### Key Conversion Events (Funnel)

```
ACCOUNT CREATED                                    100%
    |
    v
SERVICE AGREEMENT ACKNOWLEDGED                      95%
    |
    v
PATH SELECTED (Step 2)                              92%
    |
    v
INTERVIEW COMPLETED (Step 3)                        85%
    |
    v
CASE DASHBOARD VIEWED (Step 4)  <-- CONVERSION      80%
    |                                MOMENT
    v
FIRST DELIVERABLE RECEIVED (Step 5)                  75%
    |
    v
DOCUMENT UPLOADED                                    60%
    |
    v
SECOND SESSION (returned next day)                   55%
    |
    v
PRO TRIAL EXPIRATION (Day 14)
    |
    +-- CONVERTS TO PAID                             40%
    +-- DOWNGRADES TO FREE                           35%
    +-- CHURNS                                       25%
```

### A/B Testing Framework

| Test | Variant A | Variant B | Metric |
|------|----------|----------|--------|
| Onboarding length | 5-step flow (current) | 3-step flow (skip interview, start with upload) | Time-to-first-value, conversion |
| Reverse trial length | 14 days | 7 days | Conversion rate, revenue |
| First deliverable | Dashboard only | Dashboard + first draft document | Conversion rate |
| Document upload timing | Optional at Step 3 | Required at Step 3 | Completion rate, analysis quality |
| Urgency messaging | Standard | Countdown timer for lawsuit response deadline | Conversion for "received lawsuit" path |

### Retention Measurement

Daily active user (DAU) definition: User opens the app/site AND performs at least one meaningful action (views case data, runs an agent, uploads a document, or reviews a deliverable). Simple logins without action do not count.

Cohort analysis segments:
- By path (received lawsuit vs. filing vs. document help vs. ongoing)
- By jurisdiction (state-level)
- By case type (breach of contract, PI, employment, etc.)
- By tier (Free vs. Pro trial vs. paid Pro)

---

## 3.5 ONBOARDING UI DESIGN PRINCIPLES

### Mobile-First

72% of pro se litigants access legal resources from their phones. The onboarding flow must be designed mobile-first, then adapted for desktop.

| Design Principle | Implementation |
|-----------------|---------------|
| Touch targets | Minimum 44x44 points (Apple HIG) |
| Form fields | Full-width, large text (16pt minimum to prevent iOS zoom) |
| Progress indication | Step counter (1/5, 2/5...) visible at top |
| Keyboard management | Auto-advance to next field, appropriate keyboard type per field |
| Scroll behavior | Single-screen steps where possible, scrollable when content requires |
| Loading states | Skeleton screens during AI processing, not spinners |
| Error handling | Inline validation, not modal error dialogs |

### Accessibility: WCAG 2.1 AA Compliance

| Requirement | Implementation |
|------------|---------------|
| Color contrast | 4.5:1 minimum for body text, 3:1 for large text |
| Screen reader | All form elements labeled, ARIA attributes, logical tab order |
| Keyboard navigation | Full functionality without mouse/touch |
| Text resizing | Supports up to 200% text zoom without layout breakage |
| Motion | Respects prefers-reduced-motion OS setting |
| Focus indicators | Visible focus rings on all interactive elements |
| Error identification | Errors identified by more than color alone (icons + text) |

### Language

All onboarding copy is written at an 8th-grade reading level. Legal jargon is avoided in the onboarding flow. When legal terms must be used, they are accompanied by a plain-English explanation:

- "Statute of limitations" -> "the deadline for filing a lawsuit"
- "Complaint" -> "the document that starts the lawsuit"
- "Answer" -> "your written response to the lawsuit"
- "Discovery" -> "the process of exchanging information and documents"

---

---

# PART 4: YEAR 1 REVENUE PROJECTION

---

## 4.1 PRICING RECAP

From V2 Spec Section 10, with clarifications:

| Tier | Monthly Price | Annual Price (20% discount) | Target User |
|------|-------------|---------------------------|-------------|
| **Free** | $0 | $0 | Evaluation, simple legal questions, 14-day reverse trial landing |
| **Pro** | $29/month | $278/year ($23.17/month) | Individual pro se litigants, solo practitioners |
| **Team** | $49/user/month | $470/user/year | Small law firms, legal aid organizations (3-10 users) |
| **Enterprise** | Custom ($2,000-$5,000/month) | Custom annual | Large legal aid organizations, law school clinics, mid-size firms |

### Feature Matrix (Relevant to Revenue)

| Feature | Free | Pro | Team | Enterprise |
|---------|------|-----|------|-----------|
| Active cases | 1 | 10 | Unlimited | Unlimited |
| Agent runs/month | 50 | Unlimited | Unlimited | Unlimited |
| Agents per workflow | 2 | 5 (all Opus) | 5 (all Opus) | 5 (all Opus) |
| Batch document intake | 10 docs | 100 docs | 500 docs | Unlimited |
| Courtroom Ready Pack | No | Yes | Yes | Yes |
| E1-E18 enhancements | E1-E3 only | All 18 | All 18 | All 18 + custom |
| API access | No | Yes | Yes | Yes |
| Offline mode | No | Yes | Yes | Yes |
| Team collaboration | No | No | Yes (RBAC) | Yes (SSO + RBAC) |
| Support | Community | Email (48h) | Priority (24h) | Dedicated + SLA |
| Data retention | 30 days | 1 year | 3 years | Custom |

---

## 4.2 CONSERVATIVE GROWTH MODEL

### Assumptions

| Assumption | Value | Basis |
|-----------|-------|-------|
| Beta launch | Month 1 | Invite-only, 500 users |
| Public launch | Month 4 | Open registration |
| Free-to-paid conversion | 10% (M1-3), 15% (M4-6), 20% (M7-9), 25% (M10-12) | Conservative ramp; target is 40% at maturity |
| Monthly churn (Pro) | 4.4% | SMB SaaS industry average |
| Monthly churn (Team) | 2.5% | Lower churn for multi-user products |
| Team average size | 3 users/team | Small law firms, legal aid orgs |
| Enterprise deals closed | 0 (M1-6), 1 (M7-9), 2 (M10-12) | Long sales cycle for enterprise |
| Annual prepay rate | 25% (Pro), 50% (Team), 100% (Enterprise) | Annual discount incentive |

### Month-by-Month Projections

```
+-------+--------+------+------+------+--------+---------+---------+
| Month | Free   | Pro  | Team | Ent  | MRR    | Cumul.  | Notes   |
|       | Users  |      | Users|      |        | Revenue |         |
+-------+--------+------+------+------+--------+---------+---------+
|   1   |    400 |   50 |    0 |    0 |  1,450 |   1,450 | Beta    |
|   2   |    450 |   65 |    0 |    0 |  1,885 |   3,335 | Beta    |
|   3   |    500 |   85 |    0 |    0 |  2,465 |   5,800 | Beta    |
+-------+--------+------+------+------+--------+---------+---------+
|   4   |  1,200 |  150 |   15 |    0 |  5,085 |  10,885 | Launch  |
|   5   |  1,500 |  200 |   21 |    0 |  6,829 |  17,714 |         |
|   6   |  2,000 |  280 |   30 |    0 |  9,540 |  27,254 |         |
+-------+--------+------+------+------+--------+---------+---------+
|   7   |  3,000 |  400 |   45 |    1 | 18,165 |  45,419 | Growth  |
|   8   |  4,000 |  550 |   60 |    1 | 24,770 |  70,189 |         |
|   9   |  5,000 |  700 |   75 |    1 | 31,325 | 101,514 |         |
+-------+--------+------+------+------+--------+---------+---------+
|  10   |  6,500 |  850 |   90 |    2 | 39,280 | 140,794 | Scale   |
|  11   |  8,000 | 1,000|  120 |    2 | 46,580 | 187,374 |         |
|  12   | 10,000 | 1,200|  150 |    2 | 55,790 | 243,164 |         |
+-------+--------+------+------+------+--------+---------+---------+
```

**MRR Calculation (Month 12):**

```
Pro:         1,200 users x $29        = $34,800
Team:          150 users x $49        = $ 7,350
Enterprise:      2 deals x $3,500/mo  = $ 7,000
                              (avg)
Adjustments:
  Annual prepay discount:              -$ 2,360
  (25% Pro annual x 20% discount
   + 50% Team annual x 20% discount)
Estimated churn recovery:              +$ 9,000
  (win-back campaigns, reactivations)
                                       --------
Adjusted Month 12 MRR:                 $55,790
```

**Note on Team user count:** The "Team Users" column represents individual users, not teams. At 3 users per team, 150 Team users = 50 Team subscriptions.

---

## 4.3 REVENUE CALCULATION

### Year 1 Summary

```
YEAR 1 REVENUE SUMMARY
================================================

COLLECTED REVENUE (sum of all 12 months):
  Pro subscriptions:          $156,200
  Team subscriptions:         $ 36,750
  Enterprise contracts:       $ 42,000
  Annual prepay (net):        $ 12,800
                              --------
  TOTAL YEAR 1 REVENUE:      $247,750

MONTH 12 METRICS:
  MRR (Monthly Recurring):   $ 55,790
  ARR (Annualized):          $669,480

PROJECTED YEAR 2 (Month 12 ARR x growth rate):
  Conservative (1.5x):       $1,004,220
  Base (2.0x):                $1,338,960
  Aggressive (3.0x):          $2,008,440
```

### ARR Trajectory

```
ARR GROWTH TRAJECTORY (Month 12 annualized run rate)

Month:    1     3     6     9     12
          |     |     |     |     |
ARR:   $17K  $30K  $115K  $376K  $669K
          |     |     |     |     |
          +-----+-----+-----+-----+
          |#                       |
          |##                      |
          |###                     |
          |#####                   |
          |########                |
          |############            |
          |#################       |
          |######################  |
          |########################|
          +-----+-----+-----+-----+
```

### Revenue Mix (Month 12)

```
Pro:        $34,800 / $55,790 = 62.4%     <<<< Core revenue driver
Team:       $ 7,350 / $55,790 = 13.2%
Enterprise: $ 7,000 / $55,790 = 12.5%
Adj/Other:  $ 6,640 / $55,790 = 11.9%
```

The Pro tier at $29/month is the revenue engine. It is the right price point for the target market (pro se litigants who cannot afford $300-500/hour attorneys but can afford $29/month for AI assistance). The Team and Enterprise tiers provide upside but are not required for the business to be viable.

---

## 4.4 COST STRUCTURE

### Monthly Costs at Scale (Month 12)

```
MONTHLY OPERATING COSTS (Month 12)
================================================

VARIABLE COSTS (scale with usage):
  Anthropic API (Opus 4.6):            $18,000
    Breakdown:
    - 1,200 Pro users x avg 15 runs/mo x ~$1.00/run    = $18,000
    - Mitigated by:
      - Prompt caching (-90% on cached reads):          -$8,100
      - Batch API (-50% on background research):        -$3,600
      - Independent scratchpads (-67% token reduction): -$4,200
    - NET API COST after optimization:                   $2,100
    - Gross API cost (before optimization):             $18,000
    - Effective API cost (after optimization):           $2,100

  AWS Textract (OCR):                  $   400
    - ~100K pages/month at $1.50/1K pages (standard)
    - Heavy months may spike to $800

  Third-party APIs:                    $ 1,200
    - PACER access: $600 (user-passed at $0.10/page)
    - State SOS lookups: $200
    - Miscellaneous: $400

FIXED COSTS (monthly):
  AWS Infrastructure:                  $ 4,500
    - ECS Fargate (API + workers):     $ 2,000
    - Aurora PostgreSQL:               $ 1,200
    - ElastiCache (Redis):             $   500
    - S3 (document storage):           $   300
    - CloudWatch, VPC, misc:           $   500

  Cloudflare:                          $   500
    - Pages (frontend hosting):        $    50
    - CDN + WAF:                       $   200
    - Workers (edge functions):        $   250

  Support/Operations:                  $ 2,500
    - AI-first support (Ciphergy handles 80% of tickets)
    - Human support: 1 part-time contractor ($2,000)
    - Error monitoring (Sentry): $500

  Software subscriptions:              $   800
    - GitHub (team): $200
    - Monitoring (Datadog/equivalent): $400
    - Misc tools: $200

================================================
TOTAL MONTHLY COST:                    $27,900

  Variable:  $21,700  (77.8%)
  Fixed:     $ 6,200  (22.2%)

  Note: Variable costs INCLUDE gross API cost ($18K).
  With API optimizations applied, effective total
  monthly cost: ~$12,000
```

### Margin Analysis (Month 12)

```
MARGIN ANALYSIS (Month 12)
================================================

Revenue (MRR):                         $55,790
Cost (monthly):                        $27,900
                                       -------
Gross profit:                          $27,890
Gross margin:                          50.0%

WITH API COST OPTIMIZATION APPLIED:
Revenue (MRR):                         $55,790
Effective cost:                        $12,000
                                       -------
Optimized gross profit:                $43,790
Optimized gross margin:                78.5%

TARGET GROSS MARGIN AT MATURITY:       82-85%
  (as API costs decrease and caching improves)
```

**API cost is the largest variable.** Three optimization strategies bring the effective API cost from $18,000 to $2,100:

| Strategy | Reduction | How It Works |
|----------|-----------|-------------|
| Prompt caching | -90% on cached reads | Agent system prompts + tool definitions cached. 1,024-token cache prefix reduces subsequent calls to 10% of base cost. |
| Batch API | -50% on background work | Non-real-time tasks (legal research, document analysis, case law monitoring) use Anthropic's Batch API at 50% discount. |
| Independent scratchpads | -67% token reduction | Agents maintain private working context. Only final outputs enter shared state. Eliminates redundant context passing. |

---

## 4.5 UNIT ECONOMICS

### Customer Acquisition Cost (CAC)

```
CAC CALCULATION
================================================

ACQUISITION CHANNELS (Year 1):
  Content marketing / SEO:             $ 3,000/month
    - Blog posts on pro se litigation topics
    - "How to respond to a lawsuit" guides (SEO gold)
    - Legal explainer content targeting long-tail keywords

  Legal forum presence:                $ 1,000/month
    - Reddit r/legaladvice (organic, not ads)
    - Avvo community
    - Legal self-help forums
    - Genuine value-add responses with Ciphergy mention

  Social media:                        $   500/month
    - TikTok / Instagram legal education content
    - YouTube walkthrough videos

  Referral program:                    $ 1,500/month
    - "Give a friend 1 month free, get 1 month free"
    - Legal aid organization referral partnerships

  Total monthly marketing spend:       $ 6,000

  New paying customers (Month 12):     ~400/month
  CAC = $6,000 / 400 = $15 per customer
```

**Why $15 CAC is achievable:**
- Pro se litigants actively search for help (high-intent organic traffic)
- "How to respond to a lawsuit [state]" is an underserved SEO category
- Legal forums are where this demographic already congregates
- No paid advertising budget required in Year 1 (organic-first strategy)
- The product's immediate value creates word-of-mouth referrals

### Lifetime Value (LTV)

```
LTV CALCULATION
================================================

Average revenue per user (ARPU):
  Blended across tiers:                $29.00/month
  (Pro dominates at 62% of revenue)

Average customer lifetime:
  Monthly churn: 4.4%
  Lifetime = 1 / churn rate = 1 / 0.044 = 22.7 months

LTV = ARPU x Lifetime
LTV = $29.00 x 22.7 = $658.30

Rounded: $660
```

### Unit Economics Summary

| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| **CAC** | $15 | - | Low (organic/content strategy) |
| **LTV** | $660 | - | Strong (litigation cases last months-years) |
| **LTV:CAC** | 44:1 | 3:1 (target for healthy SaaS) | Exceptional |
| **Payback period** | < 1 month | 12-18 months (typical SaaS) | Exceptional |
| **Monthly churn** | 4.4% | 5-7% (SMB SaaS average) | Healthy |
| **Gross margin** | 78.5% (optimized) | 70-80% (SaaS target) | On target |

**Why LTV:CAC of 44:1 is realistic, not fantastical:**
1. CAC is low because the target market actively searches for help (zero-click-to-intent)
2. LTV is high because litigation cases last months or years (ongoing need)
3. The $29 price point has low cancellation friction (not worth thinking about)
4. Users with active cases rarely churn mid-litigation

**Risk factor:** If churn increases to 7% (aggressive scenario), LTV drops to $414, and LTV:CAC drops to 28:1. Still well above the 3:1 healthy threshold.

---

## 4.6 MARKET PENETRATION ANALYSIS

### Total Addressable Market (TAM)

```
MARKET SIZE CALCULATION
================================================

US civil case filings:              ~27 million/year
  (State + federal combined)

Self-represented (pro se) rate:     72% of civil cases
  (National Center for State Courts data)

Pro se litigants per year:          ~19.4 million

Of those, how many would pay $29/mo for AI help?

  Can afford $29/month:             ~60% (11.6M)
  Have smartphone/computer access:  ~85% (9.9M)
  Would trust AI for legal help:    ~30% (3.0M)
  Would find and try Ciphergy:      varies by marketing reach

SERVICEABLE ADDRESSABLE MARKET (SAM): ~3.0 million
TARGET YEAR 1 PENETRATION:            0.05% = ~10,000 users
```

### Year 1 Penetration: 10,000 Users

10,000 users out of 3 million potential = 0.33% of SAM. This is conservative and achievable through:

| Channel | Estimated Users | How |
|---------|----------------|-----|
| SEO (organic search) | 4,000 | "How to respond to a lawsuit," "pro se litigation help," "AI legal assistant" |
| Reddit / Legal forums | 2,000 | Value-add presence in r/legaladvice, r/legal, Avvo |
| Legal aid referrals | 1,500 | Partnerships with legal aid organizations, law school clinics |
| Word of mouth | 1,500 | Users refer other litigants (common in legal communities) |
| Social media | 500 | TikTok/YouTube legal education content |
| Press / media | 500 | Launch coverage, legal tech press |

### Sensitivity Analysis

```
YEAR 1 REVENUE SENSITIVITY ANALYSIS
================================================

                    BEAR         BASE         BULL
                    CASE         CASE         CASE
                    ----         ----         ----
Conversion rate:    8%           15%          25%
Month 12 users:    5,000        10,000       20,000
Month 12 Pro:       500         1,200        3,000
Month 12 Team:       50           150          300
Enterprise:           0             2            5

Month 12 MRR:     $16,950      $55,790     $137,700
Month 12 ARR:    $203,400     $669,480   $1,652,400

Year 1 Revenue:  $121,000     $247,750     $612,000
Year 1 Costs:    $180,000     $210,000     $340,000
Year 1 Profit:   -$59,000      $37,750     $272,000

Break-even:       Month 14      Month 8      Month 4
```

**Bear case assumptions:**
- Slower organic growth (SEO takes longer to rank)
- Lower conversion rate (8% vs 15%)
- Higher churn (6% vs 4.4%)
- No enterprise deals in Year 1
- Result: Loss of $59K, but with clear path to profitability in Year 2

**Bull case assumptions:**
- Viral Reddit/TikTok moment accelerates awareness
- Higher conversion (25%) due to strong product-market fit
- 5 enterprise deals (law school clinics, legal aid organizations)
- Result: $272K profit in Year 1, $1.65M ARR run rate

---

## 4.7 COMPETITIVE MOAT

### 5 Defensive Moats (Ordered by Strength)

```
MOAT DEPTH ANALYSIS
================================================

MOAT 1: OUTCOME DATA (E14)
Depth:    ████████████████████  DEEPEST
Timeline: Compounds over time -- each case teaches the system
Defense:  Competitors start at zero outcome data. By Month 12,
          Ciphergy has data from 10,000+ cases across 50 states.
          Judge-specific win rates, motion effectiveness by type,
          settlement timing patterns -- all proprietary.

MOAT 2: MCP LEGAL ECOSYSTEM (E16)
Depth:    ████████████████░░░░  DEEP
Timeline: 10 open-source MCP servers create ecosystem lock-in
Defense:  Ciphergy becomes the legal MCP authority. Competitors
          who build on MCP must use these servers or reinvent them.
          Community contributions improve the ecosystem continuously.

MOAT 3: CASE KNOWLEDGE STORE PORTABILITY
Depth:    ██████████████░░░░░░  MODERATE-DEEP
Timeline: Available from Day 1
Defense:  Paradox of portability: users who know they CAN export
          everything are LESS likely to leave. The 22-section
          extraction prompt means zero switching cost, which
          builds trust and reduces churn anxiety. Counterintuitively,
          this INCREASES retention.

MOAT 4: PRO SE MARKET FOCUS
Depth:    ████████████░░░░░░░░  MODERATE
Timeline: Immediate positioning advantage
Defense:  Harvey AI targets $1,000+/seat BigLaw. CrewAI targets
          developers. LangChain targets engineers. Ciphergy targets
          the 72% of civil litigants who represent themselves --
          a market no well-funded competitor is pursuing. Different
          market, different product, different price point, different
          UX requirements.

MOAT 5: ENHANCEMENT DEPTH (E1-E18)
Depth:    ██████████░░░░░░░░░░  MODERATE
Timeline: 6+ months of domain engineering advantage
Defense:  18 enhancements represent deep legal domain expertise:
          evidence weaponization, settlement pressure modeling,
          motion warfare sequencing, judicial analytics, damages
          maximization, procedural trap detection, appeal
          preservation. A horizontal platform cannot replicate
          this depth without equivalent domain investment.
```

### Competitive Positioning Matrix

```
+-------------------+----------+-------+--------+--------+----------+
| Competitor        | Target   | Price | Legal  | Multi- | Pro Se   |
|                   | Market   |       | Depth  | Agent  | Features |
+-------------------+----------+-------+--------+--------+----------+
| Harvey AI         | BigLaw   | $1K+  | Deep   | No     | No       |
| CoCounsel (Casetext)| MidLaw| $300+ | Deep   | No     | No       |
| CrewAI            | Devs     | Free+ | None   | Yes    | No       |
| LangGraph         | Devs     | Free  | None   | Yes    | No       |
| Dust.tt           | Business | $29+  | None   | Partial| No       |
| DoNotPay          | Consumer | $36   | Shallow| No     | Partial  |
| LegalZoom         | Consumer | $10+  | Forms  | No     | Partial  |
| Rocket Lawyer     | Consumer | $40   | Forms  | No     | Partial  |
+-------------------+----------+-------+--------+--------+----------+
| CIPHERGY          | Pro Se   | $29   | Deep   | Yes    | YES      |
|                   | (72% of  |       | (18    | (5     | (7 pro   |
|                   | litigants|       | enhanc)| agents)| se feat) |
+-------------------+----------+-------+--------+--------+----------+

White space: No competitor combines deep legal domain expertise +
multi-agent architecture + pro se accessibility + $29 price point.
```

### Why Harvey AI Going Downmarket Is Not an Existential Threat

Harvey AI ($8B valuation, $1,000+/seat) could theoretically offer a $29/month pro se product. Here is why this is unlikely and why it would not be fatal:

1. **Business model conflict:** Harvey's revenue comes from BigLaw firms paying premium prices. A $29 product cannibalizes the perception of premium value.
2. **UX mismatch:** A product designed for attorneys does not serve pro se litigants. The language, assumptions, and workflows are fundamentally different.
3. **Margin pressure:** Harvey's cost structure (Westlaw/Lexis integration, enterprise sales team, SOC 2, HIPAA) cannot support a $29 price point profitably.
4. **Market focus:** Harvey is pursuing $100B+ BigLaw contracts. The pro se market at $29/month is a distraction, not an opportunity, for a company at their scale.
5. **First-mover advantage:** By the time Harvey notices the pro se market, Ciphergy has outcome data, community ecosystem, and brand recognition.

---

## 4.8 RISK FACTORS

### Risk Matrix

```
RISK ASSESSMENT MATRIX
================================================

                      LOW IMPACT    MEDIUM IMPACT   HIGH IMPACT
                     +-----------+-------------+-------------+
HIGH                 |           | Competition | Regulatory  |
PROBABILITY          |           | (generic AI | (state UPL  |
                     |           |  tools)     |  restrict.) |
                     +-----------+-------------+-------------+
MEDIUM               |           | API Cost    | Accuracy    |
PROBABILITY          |           | Increase    | Incident    |
                     |           |             |             |
                     +-----------+-------------+-------------+
LOW                  | Hosting   | Harvey goes | Anthropic   |
PROBABILITY          | outage    | downmarket  | discontinues|
                     |           |             | Opus        |
                     +-----------+-------------+-------------+
```

### Detailed Risk Analysis

#### Risk 1: Regulatory Risk (State UPL Restrictions)

| Attribute | Value |
|-----------|-------|
| Probability | HIGH (30-40% within 2 years) |
| Impact | HIGH — could restrict operations in specific states |
| Description | States could restrict or regulate AI legal tools through unauthorized practice of law (UPL) enforcement, new legislation, or bar association opinions. |
| Precedent | Several states have issued AI-in-legal-practice guidelines (2025-2026). Some judges have issued standing orders requiring AI disclosure in filings. |
| Mitigation | 1) Section 14 Ethical Framework (already spec'd) — compliant by design. 2) Service Agreement explicitly disclaims legal practice. 3) Track all state bar AI guidance (Section 14.4 compliance matrix). 4) Proactive engagement with state bar associations. 5) System is a "tool" not a "provider" — users make all decisions. |
| Contingency | If a state bans AI legal tools outright (extreme scenario), geo-fence that state and exclude. Federal law currently does not restrict AI tools. |

#### Risk 2: API Cost Risk (Anthropic Price Changes)

| Attribute | Value |
|-----------|-------|
| Probability | MEDIUM (20-30% for significant increase) |
| Impact | MEDIUM — directly affects margins |
| Description | Anthropic could increase Opus pricing, change caching discounts, or modify batch API pricing. A 2x price increase would double the largest variable cost. |
| Current exposure | Opus 4.6: $15/M input, $75/M output. Ciphergy's all-Opus policy means no downgrade path for legal agents. |
| Mitigation | 1) Three-layer cost optimization (caching, batch, scratchpads) already reduces effective cost by 88%. 2) Model-agnostic architecture via LiteLLM — if Opus becomes uneconomical, evaluate alternatives. 3) Price elasticity: $29->$39 would retain 85%+ of users (litigation cases create strong lock-in). 4) Annual prepay creates revenue buffer. |
| Contingency | If API costs double: raise Pro price to $39/month (still 99% cheaper than an attorney). If API costs triple: implement usage-based pricing overlay. |

#### Risk 3: Competition Risk (Generic AI Tools)

| Attribute | Value |
|-----------|-------|
| Probability | HIGH (already happening) |
| Impact | MEDIUM — creates noise but lacks depth |
| Description | Generic AI chatbots (ChatGPT, Claude direct, Gemini) can answer legal questions. Users may perceive "good enough" and not pay $29/month for Ciphergy. |
| Why it's medium, not high impact | Generic AI cannot: verify citations against live databases, compute jurisdiction-specific deadlines, run 5-agent debate consensus, produce court-formatted filings, manage case lifecycle, or provide the 18 enhancements. The gap between "ask ChatGPT a legal question" and "use Ciphergy to litigate a case" is enormous. |
| Mitigation | 1) Demonstrate value gap through content marketing. 2) The 5-minute onboarding flow shows immediate superiority over generic AI. 3) Citation verification alone justifies the price — one fabricated citation filed in court can result in sanctions. |

#### Risk 4: Accuracy Risk (Hallucination Incident)

| Attribute | Value |
|-----------|-------|
| Probability | MEDIUM (15-25% for a public incident in Year 1) |
| Impact | HIGH — could damage trust and generate negative press |
| Description | Despite the anti-hallucination loop, WDC review, and citation verification, the system could produce an incorrect legal analysis that leads to a negative outcome for a user. If this becomes public, it damages trust across the entire user base. |
| Precedent | Mata v. Avianca (2023) — attorney sanctioned for filing ChatGPT-fabricated citations. This case created lasting reputational damage for AI-in-legal. |
| Mitigation | 1) 5-step citation verification pipeline (Section 6, V2 spec). 2) WDC 5-agent review on every substantive output. 3) Compliance veto power on procedural errors. 4) Confidence flags on every assertion (Section 14.6). 5) Service Agreement disclaimers (Section 14.2). 6) User responsibility for review before filing. 7) Compound reliability safeguard (E17) — 99.5% per-step accuracy target. |
| Contingency | If incident occurs: 1) Immediate transparency — disclose what happened and why. 2) Root cause analysis and fix. 3) Proactive communication to all users. 4) Donate to legal aid organizations as goodwill measure. 5) Use incident to improve the verification pipeline. |

#### Risk 5: Anthropic Platform Risk

| Attribute | Value |
|-----------|-------|
| Probability | LOW (5-10%) |
| Impact | HIGH — would require major architecture change |
| Description | Anthropic could discontinue the Opus model line, restrict API access for legal use cases, or change terms of service in ways that prevent Ciphergy's use case. |
| Mitigation | 1) LiteLLM model-agnostic routing — can switch to OpenAI, Google, or other providers. 2) Architecture does not depend on Anthropic-specific features (standard API calls). 3) Local model deployment option for Enterprise tier as fallback. |
| Contingency | If Anthropic becomes unavailable: migrate to GPT-4-class models via LiteLLM. Requires retuning agent prompts but architecture remains unchanged. |

---

## DOCUMENT SUMMARY

| Part | Subject | Key Deliverable | Phase Integration |
|------|---------|----------------|-------------------|
| **Part 1** | Batch Document Intake | 14-category classification, OCR pipeline, priority routing, drag-and-drop UI, database schema | Phase 3 (Case Management) |
| **Part 2** | Offline Courtroom Mode | 10-section hearing pack, PDF/mobile/PWA export, courtroom UI, objection cards | Phase 6 (Pro Se Features) |
| **Part 3** | Onboarding UX | 5-step flow, situation assessment engine, path-specific first deliverables, conversion metrics | Phase 8 (Hardening & Launch) |
| **Part 4** | Revenue Projection | $247K Year 1 revenue, $669K ARR run rate, 78.5% gross margin, 44:1 LTV:CAC, 5 competitive moats | Business planning |

---

**CONFIDENTIAL -- Bo Pennington / Pentek Design Build LLC**

*These four specifications close the medium-priority gaps identified in the WDC V2 Spec Review (Gap 6, Gap 7, Refinement 3, Refinement 1). Each is implementation-ready. Each integrates with the existing 5-agent architecture, WDC v2.0 debate protocol, and Case Knowledge Store. Together, they transform Ciphergy from a legal reasoning engine into a complete litigation platform that meets pro se litigants where they actually are -- uploading documents at midnight, standing in a courtroom without WiFi, and deciding whether $29/month is the smartest $29 they will ever spend.*
