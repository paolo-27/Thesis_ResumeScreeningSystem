-- ============================================================
-- Veridian RSS — Supabase One-Time Setup
-- Run this ONCE in the Supabase SQL Editor before starting the app.
-- ============================================================

-- Step 1: Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify it was created
SELECT * FROM pg_extension WHERE extname = 'vector';
