-- Migration: 011_learning_loop_schema.sql
-- Task: Learning Loop Schema Enhancements
-- Description: Add idea_id to decomposed_creatives and death_state to ideas

-- ============================================
-- 1. Add idea_id to decomposed_creatives for direct JOIN
-- ============================================

ALTER TABLE genomai.decomposed_creatives
ADD COLUMN IF NOT EXISTS idea_id uuid REFERENCES genomai.ideas(id);

CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_idea_id
ON genomai.decomposed_creatives(idea_id);

COMMENT ON COLUMN genomai.decomposed_creatives.idea_id IS 'Direct reference to idea (denormalized from payload for efficient JOINs)';

-- ============================================
-- 2. Add death_state to ideas
-- ============================================

ALTER TABLE genomai.ideas
ADD COLUMN IF NOT EXISTS death_state text
CHECK (death_state IS NULL OR death_state IN ('soft_dead', 'hard_dead', 'permanent_dead'));

CREATE INDEX IF NOT EXISTS idx_ideas_death_state
ON genomai.ideas(death_state)
WHERE death_state IS NOT NULL;

COMMENT ON COLUMN genomai.ideas.death_state IS 'Death state: NULL=alive, soft_dead=3 failures, hard_dead=5 failures after resurrection, permanent_dead=human override';

-- ============================================
-- 3. Add change_reason to idea_confidence_versions
-- ============================================

ALTER TABLE genomai.idea_confidence_versions
ADD COLUMN IF NOT EXISTS change_reason text;

COMMENT ON COLUMN genomai.idea_confidence_versions.change_reason IS 'Reason for confidence change (e.g., learning_applied, manual_override)';

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  -- Verify idea_id column exists
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'decomposed_creatives'
    AND column_name = 'idea_id'
  ) THEN
    RAISE EXCEPTION 'Column idea_id was not added to decomposed_creatives';
  END IF;

  -- Verify death_state column exists
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'ideas'
    AND column_name = 'death_state'
  ) THEN
    RAISE EXCEPTION 'Column death_state was not added to ideas';
  END IF;

  RAISE NOTICE 'Migration 011_learning_loop_schema completed successfully';
END $$;
