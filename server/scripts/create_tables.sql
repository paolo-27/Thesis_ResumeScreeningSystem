-- ============================================================
-- Veridian RSS — PostgreSQL Table Definitions (Supabase)
-- Run this AFTER setup_supabase.sql (pgvector must be enabled first).
-- Run in Supabase SQL Editor or via psql.
-- ============================================================

-- ──────────────────────────────────────────
-- 1. Users
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    employee_number TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    company         TEXT,
    location        TEXT,
    avatar_color    TEXT DEFAULT '#10b981',
    role            TEXT DEFAULT 'HR',           -- 'Admin' | 'HR'
    is_active       INTEGER DEFAULT 1,           -- 1 = active, 0 = deactivated
    force_reset     INTEGER DEFAULT 0,           -- 1 = must reset password on next login
    created_at      TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US')
);

CREATE INDEX IF NOT EXISTS idx_users_employee_number ON users(employee_number);

-- ──────────────────────────────────────────
-- 2. Jobs
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    title               TEXT NOT NULL,
    department          TEXT NOT NULL,
    location            TEXT NOT NULL,
    type                TEXT NOT NULL,
    status              TEXT DEFAULT 'Active',   -- 'Active' | 'Draft' | 'Closed'
    "applicantsCount"   INTEGER DEFAULT 0,
    "postedDate"        TEXT NOT NULL,
    description         TEXT,
    requirements        TEXT,
    salary              TEXT,
    "parsedRequirements" TEXT,
    created_by_id       TEXT REFERENCES users(id),
    embedding           vector(384)              -- SBERT all-MiniLM-L6-v2 embeddings
);

CREATE INDEX IF NOT EXISTS idx_jobs_created_by ON jobs(created_by_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status     ON jobs(status);

-- ──────────────────────────────────────────
-- 3. Candidates
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    name              TEXT NOT NULL,
    email             TEXT NOT NULL,
    phone             TEXT,
    applied_job_id    TEXT REFERENCES jobs(id),
    probability_score DOUBLE PRECISION NOT NULL,
    gyr_tier          TEXT NOT NULL,            -- 'Green' | 'Yellow' | 'Red'
    status            TEXT DEFAULT 'Pending',   -- 'Pending' | 'Shortlisted' | 'Rejected'
    resume_url        TEXT,
    "appliedDate"     TEXT NOT NULL,
    embedding         vector(384)               -- SBERT resume embedding
);

CREATE INDEX IF NOT EXISTS idx_candidates_job_id  ON candidates(applied_job_id);
CREATE INDEX IF NOT EXISTS idx_candidates_gyr_tier ON candidates(gyr_tier);
CREATE INDEX IF NOT EXISTS idx_candidates_status   ON candidates(status);

-- pgvector IVFFlat index for fast cosine similarity search on candidate embeddings
-- (Create AFTER initial data load for best index quality)
-- CREATE INDEX IF NOT EXISTS idx_candidates_embedding
--     ON candidates USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ──────────────────────────────────────────
-- 4. Activity Logs
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_logs (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id     TEXT,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    timestamp   TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US')
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id   ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
