-- Migration: 000_all_tables.sql
-- Purpose: Reference file - DO NOT EXECUTE DIRECTLY
-- WARNING: This file is for reference only. 
-- 
-- IMPORTANT: This file uses \i commands which only work in psql CLI.
-- For Supabase SQL Editor, apply migrations individually:
-- 1. Open 001_event_log.sql → Copy → Paste → Run
-- 2. Open 002_core_tables.sql → Copy → Paste → Run
-- 3. ... and so on
--
-- For psql CLI usage:
-- psql "your-connection-string" -f infrastructure/migrations/001_event_log.sql
-- psql "your-connection-string" -f infrastructure/migrations/002_core_tables.sql
-- ... etc
--
-- RECOMMENDED: Apply migrations one by one to catch errors early.

-- ============================================
-- Migration Order
-- ============================================

-- 1. 001_event_log.sql          - Event logging infrastructure
-- 2. 002_core_tables.sql        - creatives, ideas
-- 3. 003_transcription.sql      - transcripts, decomposed_creatives
-- 4. 004_metrics.sql            - raw_metrics_current, daily_metrics_snapshot
-- 5. 005_outcomes.sql           - outcome_aggregates
-- 6. 006_learning.sql           - idea_confidence_versions, fatigue_state_versions
-- 7. 007_hypotheses.sql         - hypotheses, deliveries

-- ============================================
-- Verification Query (run after all migrations)
-- ============================================

-- Run this query to verify all tables were created:
/*
SELECT 
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns 
   WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_name IN (
    'event_log',
    'creatives',
    'ideas',
    'transcripts',
    'decomposed_creatives',
    'raw_metrics_current',
    'daily_metrics_snapshot',
    'outcome_aggregates',
    'idea_confidence_versions',
    'fatigue_state_versions',
    'hypotheses',
    'deliveries'
  )
ORDER BY table_name;
*/

-- Expected result: 12 tables

