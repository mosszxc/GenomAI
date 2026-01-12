-- Migration: 039_learning_idempotency.sql
-- Task: #473 - Learning Loop idempotency fix
-- Description: Add unique constraints on source_outcome_id to prevent duplicate processing

-- ============================================
-- Problem
-- ============================================
-- When Temporal activity fails after processing an outcome but before returning,
-- retry processes the same outcome again, creating duplicate confidence/fatigue versions.
--
-- Solution: Add unique index on source_outcome_id to enforce one version per outcome.

-- ============================================
-- 1. Unique index on idea_confidence_versions.source_outcome_id
-- ============================================

-- First, clean up any existing duplicates (keep only the first one)
-- This is needed for existing data that may have duplicates
DELETE FROM genomai.idea_confidence_versions a
USING genomai.idea_confidence_versions b
WHERE a.source_outcome_id = b.source_outcome_id
  AND a.id > b.id;

-- Add unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_idea_confidence_versions_outcome_unique
ON genomai.idea_confidence_versions(source_outcome_id);

COMMENT ON INDEX genomai.idx_idea_confidence_versions_outcome_unique IS
'Idempotency guard: ensures each outcome produces exactly one confidence version. See issue #473.';

-- ============================================
-- 2. Unique index on fatigue_state_versions.source_outcome_id
-- ============================================

-- Clean up any existing duplicates
DELETE FROM genomai.fatigue_state_versions a
USING genomai.fatigue_state_versions b
WHERE a.source_outcome_id = b.source_outcome_id
  AND a.id > b.id;

-- Add unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_fatigue_state_versions_outcome_unique
ON genomai.fatigue_state_versions(source_outcome_id);

COMMENT ON INDEX genomai.idx_fatigue_state_versions_outcome_unique IS
'Idempotency guard: ensures each outcome produces exactly one fatigue version. See issue #473.';

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  -- Verify idx_idea_confidence_versions_outcome_unique exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'genomai'
    AND tablename = 'idea_confidence_versions'
    AND indexname = 'idx_idea_confidence_versions_outcome_unique'
  ) THEN
    RAISE EXCEPTION 'Index idx_idea_confidence_versions_outcome_unique was not created';
  END IF;

  -- Verify idx_fatigue_state_versions_outcome_unique exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'genomai'
    AND tablename = 'fatigue_state_versions'
    AND indexname = 'idx_fatigue_state_versions_outcome_unique'
  ) THEN
    RAISE EXCEPTION 'Index idx_fatigue_state_versions_outcome_unique was not created';
  END IF;

  RAISE NOTICE 'Migration 039_learning_idempotency completed successfully';
END $$;
