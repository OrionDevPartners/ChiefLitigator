# ChiefLitigator: Auto-Siphon Pipeline & "If-Then" Matching Architecture

**Prepared for:** ChiefLitigator.com / ChiefLitigator.ai
**Date:** March 19, 2026

---

## 1. The Auto-Siphon Pipeline

The Auto-Siphon Pipeline is the data ingestion engine that feeds the Jurisdiction Containers. It continuously pulls every Supreme Court ruling, circuit court ruling, state court ruling, statute, and rule into the AWS Aurora database for instant, zero-latency recall.

### 1.1 Data Sources & Ingestion Methods

| Source | Data Type | Ingestion Method | Frequency |
| :--- | :--- | :--- | :--- |
| **CourtListener / Free Law Project** | Federal & State Case Law (8M+ opinions) | Bulk JSON download (initial) + REST API (updates) | Daily |
| **Harvard Caselaw Access Project** | Historical Case Law (1658-2018) | Bulk JSON download (one-time) | Static |
| **US Code (OLRC)** | Federal Statutes | Bulk XML download | On release |
| **GovInfo.gov** | CFR, Federal Register, Public Laws | REST API | Daily |
| **LegiScan** | State Statutes (All 50 States) | REST API / Bulk JSON | Weekly |
| **US Courts (uscourts.gov)** | FRCP, FRE, FRAP, FRCrP | Web Scraping (PDF/HTML parsing) | On amendment |
| **USCIS / EOIR** | Immigration Rules, BIA Precedent | Web Scraping / API | Weekly |

### 1.2 Pipeline Architecture (AWS Native)

1.  **EventBridge Scheduler:** Triggers the siphon lambdas on their respective schedules (daily, weekly, etc.).
2.  **AWS Lambda (Siphon Workers):** Python-based workers that connect to the APIs, download the raw data (JSON, XML, PDF), and normalize it into a standard ChiefLitigator schema.
3.  **AWS S3 (Raw Storage):** Stores the raw, unmodified downloaded files as a permanent backup and audit trail.
4.  **AWS Aurora PostgreSQL (The Knowledge Graph):** The normalized data is inserted into Aurora. This is where the "instant recall" happens. No API calls are made during a user session to fetch law; it is all queried locally from Aurora.
5.  **pgvector (Semantic Indexing):** As data is inserted into Aurora, an AWS Bedrock embedding model generates vector embeddings for the text, allowing for semantic search.

---

## 2. The "If-Then" Matching Algorithm

The core intelligence of ChiefLitigator is the "If-Then" matching algorithm. It translates a user's messy, real-world context into structured legal strategy by traversing the data stored in Aurora.

### 2.1 The Translation Layer

When a user provides context (e.g., "My landlord changed the locks while I was at work"), the system does not just do a keyword search for "landlord" and "locks."

1.  **Fact Extraction (Bedrock LLM):** The Intake Agent extracts the core facts: `[Entity: Landlord]`, `[Action: Changed locks]`, `[Status: Tenant absent]`.
2.  **Semantic Vector Search (pgvector):** The extracted facts are converted to a vector and queried against the Aurora `statutes` and `case_law` tables using cosine similarity.
3.  **The "If-Then" Matrix:** The system evaluates the retrieved law against the facts.
    *   *IF* `jurisdiction == Florida` AND `action == lockout` AND `process == extrajudicial`,
    *   *THEN* `statute == FL Stat 83.67` AND `cause_of_action == Wrongful Eviction` AND `remedy == 3x rent or actual damages`.

### 2.2 The Procedural Inference Engine

Once the statute and cause of action are identified, the algorithm infers the required procedures and deadlines.

1.  **Rule Matching:** The system queries the `court_rules` table in Aurora for the specific jurisdiction.
    *   *IF* `cause_of_action == Wrongful Eviction (Emergency)`,
    *   *THEN* `document_type == Emergency Motion for Possession` AND `filing_court == County Court`.
2.  **Deadline Calculation:** The Deadline Sentinel calculates the exact dates based on the inferred rules.
    *   *IF* `document_type == Emergency Motion`,
    *   *THEN* `response_time == Immediate/Ex Parte` OR `hearing_time == within 5 days`.

---

## 3. Storage Architecture: Aurora vs. DynamoDB

To ensure maximum performance and cost-efficiency, data is strictly segregated between AWS Aurora and AWS DynamoDB.

### 3.1 AWS Aurora PostgreSQL (The Heavy Lifter)

Aurora holds the massive, structured, relational legal data. This is the "brain" of the system.

*   **Tables:** `case_law`, `statutes`, `court_rules`, `jurisdictions`, `legal_concepts`.
*   **Extensions:** `pgvector` for semantic search.
*   **Characteristics:** High read volume, complex relational queries (e.g., finding all cases that cite a specific statute and were decided after 2020), massive storage capacity.

### 3.2 AWS DynamoDB (The Fast User State)

DynamoDB holds the lightweight, highly transactional user data.

*   **Tables:** `user_sessions`, `active_cases`, `document_drafts` (metadata only, actual files in S3), `wdc_debate_logs`.
*   **Characteristics:** Key-value lookups, millisecond latency, highly scalable for concurrent user sessions.
*   **Usage:** When a user logs in, their active case state is instantly loaded from DynamoDB. When the WDC engine runs a Galvanizer loop, the intermediate debate states are rapidly written to DynamoDB.

---

## 4. Implementation Next Steps

1.  **Database Schema:** Define the SQLAlchemy models for the Aurora `case_law` and `statutes` tables, including the `pgvector` columns.
2.  **Siphon Scripts:** Write the initial Python scripts to pull data from the CourtListener API and the US Code XML bulk download.
3.  **Matching Logic:** Implement the core `IfThenMatcher` class that takes extracted facts and queries the Aurora vector database.
