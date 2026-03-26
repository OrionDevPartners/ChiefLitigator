"""001 — Legal Knowledge Graph Tables (Aurora PostgreSQL + pgvector).

Creates the foundational tables for the auto-siphon pipeline:
  - statutes: Federal and state statutes with vector embeddings
  - case_law: Court opinions with vector embeddings
  - court_rules: Procedural rules with vector embeddings
  - siphon_runs: Audit trail for siphon pipeline executions
  - if_then_rules: Materialized matching rules (fact → statute → procedure)

Requires: CREATE EXTENSION IF NOT EXISTS vector;
"""

from __future__ import annotations

UPGRADE_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────
-- Statutes table (Federal + 50 states)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS statutes (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,          -- 'uscode', 'legiscan', 'cfr'
    jurisdiction    VARCHAR(10) NOT NULL,           -- 'US', 'FL', 'TX', etc.
    title_number    VARCHAR(20),                    -- Title number (e.g., '42')
    section         VARCHAR(100) NOT NULL,          -- Section identifier
    heading         TEXT NOT NULL,                   -- Section heading
    body_text       TEXT NOT NULL,                   -- Full text of the statute
    effective_date  DATE,
    repeal_date     DATE,
    embedding       vector(1536),                   -- Titan Embeddings V2
    metadata        JSONB DEFAULT '{}',
    siphon_run_id   BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, jurisdiction, section)
);

CREATE INDEX idx_statutes_jurisdiction ON statutes(jurisdiction);
CREATE INDEX idx_statutes_source ON statutes(source);
CREATE INDEX idx_statutes_embedding ON statutes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 200);

-- ─────────────────────────────────────────────────────────────
-- Case Law table (SCOTUS, Circuit, State)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS case_law (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,           -- 'courtlistener', 'cap', 'scotus'
    source_id       VARCHAR(100),                   -- External ID from source
    case_name       TEXT NOT NULL,
    citation        VARCHAR(200),                   -- Official citation
    court           VARCHAR(200) NOT NULL,          -- Court name
    court_level     VARCHAR(20) NOT NULL,           -- 'scotus', 'circuit', 'district', 'state_supreme', 'state_appellate', 'state_trial'
    jurisdiction    VARCHAR(10) NOT NULL,            -- 'US', 'FL', etc.
    date_decided    DATE,
    opinion_text    TEXT NOT NULL,
    holding         TEXT,                            -- Extracted holding
    headnotes       TEXT[],                          -- Key legal points
    cited_statutes  VARCHAR(200)[],                 -- Statutes cited in opinion
    cited_cases     VARCHAR(200)[],                 -- Cases cited in opinion
    embedding       vector(1536),
    metadata        JSONB DEFAULT '{}',
    siphon_run_id   BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, source_id)
);

CREATE INDEX idx_case_law_jurisdiction ON case_law(jurisdiction);
CREATE INDEX idx_case_law_court_level ON case_law(court_level);
CREATE INDEX idx_case_law_court ON case_law(court);
CREATE INDEX idx_case_law_date ON case_law(date_decided);
CREATE INDEX idx_case_law_citation ON case_law(citation);
CREATE INDEX idx_case_law_embedding ON case_law USING ivfflat (embedding vector_cosine_ops) WITH (lists = 500);

-- ─────────────────────────────────────────────────────────────
-- Court Rules table (FRCP, FRAP, FRE, state rules)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS court_rules (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,
    jurisdiction    VARCHAR(10) NOT NULL,
    rule_set        VARCHAR(100) NOT NULL,          -- 'FRCP', 'FRAP', 'FRE', 'FL_RCP', etc.
    rule_number     VARCHAR(50) NOT NULL,
    rule_title      TEXT NOT NULL,
    rule_text       TEXT NOT NULL,
    deadlines       JSONB DEFAULT '[]',             -- Extracted deadlines [{days: 21, trigger: "service", description: "Answer"}]
    embedding       vector(1536),
    metadata        JSONB DEFAULT '{}',
    siphon_run_id   BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, jurisdiction, rule_set, rule_number)
);

CREATE INDEX idx_court_rules_jurisdiction ON court_rules(jurisdiction);
CREATE INDEX idx_court_rules_rule_set ON court_rules(rule_set);
CREATE INDEX idx_court_rules_embedding ON court_rules USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─────────────────────────────────────────────────────────────
-- Siphon Runs (audit trail)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS siphon_runs (
    id              BIGSERIAL PRIMARY KEY,
    worker_name     VARCHAR(100) NOT NULL,          -- 'courtlistener', 'uscode', etc.
    status          VARCHAR(20) NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'failed'
    records_fetched INTEGER DEFAULT 0,
    records_stored  INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_siphon_runs_worker ON siphon_runs(worker_name);
CREATE INDEX idx_siphon_runs_status ON siphon_runs(status);

-- ─────────────────────────────────────────────────────────────
-- If-Then Rules (materialized matching rules)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS if_then_rules (
    id              BIGSERIAL PRIMARY KEY,
    jurisdiction    VARCHAR(10) NOT NULL,
    practice_area   VARCHAR(100) NOT NULL,          -- 'eviction', 'breach_of_contract', 'immigration', etc.
    fact_pattern    TEXT NOT NULL,                   -- "IF landlord changed locks without notice"
    applicable_law  TEXT NOT NULL,                   -- "THEN FL Stat. 83.67 (unlawful lockout)"
    procedure       TEXT NOT NULL,                   -- "File emergency motion for possession"
    deadline_days   INTEGER,                         -- Days from trigger event
    deadline_trigger VARCHAR(200),                   -- What triggers the deadline
    document_type   VARCHAR(100),                    -- 'emergency_motion', 'complaint', 'answer', etc.
    confidence      FLOAT DEFAULT 0.0,              -- Confidence in this rule (0.0-1.0)
    source_statute_id  BIGINT REFERENCES statutes(id),
    source_case_id     BIGINT REFERENCES case_law(id),
    source_rule_id     BIGINT REFERENCES court_rules(id),
    embedding       vector(1536),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_if_then_jurisdiction ON if_then_rules(jurisdiction);
CREATE INDEX idx_if_then_practice_area ON if_then_rules(practice_area);
CREATE INDEX idx_if_then_embedding ON if_then_rules USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─────────────────────────────────────────────────────────────
-- Cross-reference table (statute ↔ case_law ↔ court_rule)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legal_cross_references (
    id              BIGSERIAL PRIMARY KEY,
    statute_id      BIGINT REFERENCES statutes(id),
    case_law_id     BIGINT REFERENCES case_law(id),
    court_rule_id   BIGINT REFERENCES court_rules(id),
    relationship    VARCHAR(50) NOT NULL,           -- 'interprets', 'cites', 'overrules', 'implements'
    confidence      FLOAT DEFAULT 0.0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_xref_statute ON legal_cross_references(statute_id);
CREATE INDEX idx_xref_case ON legal_cross_references(case_law_id);
CREATE INDEX idx_xref_rule ON legal_cross_references(court_rule_id);
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS legal_cross_references CASCADE;
DROP TABLE IF EXISTS if_then_rules CASCADE;
DROP TABLE IF EXISTS siphon_runs CASCADE;
DROP TABLE IF EXISTS court_rules CASCADE;
DROP TABLE IF EXISTS case_law CASCADE;
DROP TABLE IF EXISTS statutes CASCADE;
"""


async def upgrade(connection) -> None:
    """Run the upgrade migration."""
    await connection.execute(UPGRADE_SQL)


async def downgrade(connection) -> None:
    """Run the downgrade migration."""
    await connection.execute(DOWNGRADE_SQL)
