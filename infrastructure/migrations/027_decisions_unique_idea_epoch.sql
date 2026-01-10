-- Migration: Add UNIQUE constraint on (idea_id, decision_epoch) to prevent duplicate decisions
-- Issue: #284 - Excessive decisions on single idea (8 decisions for one idea_id)
--
-- This migration:
-- 1. Deletes duplicate decisions, keeping only the first (oldest) one for each (idea_id, decision_epoch)
-- 2. Adds a UNIQUE constraint to prevent future duplicates

-- Step 1: Delete duplicate decisions (keep the oldest one)
-- First, delete the orphaned decision_traces
DELETE FROM genomai.decision_traces
WHERE decision_id IN (
    SELECT d.id
    FROM genomai.decisions d
    WHERE d.id NOT IN (
        SELECT DISTINCT ON (idea_id, decision_epoch) id
        FROM genomai.decisions
        ORDER BY idea_id, decision_epoch, created_at ASC
    )
);

-- Then delete the duplicate decisions
DELETE FROM genomai.decisions
WHERE id NOT IN (
    SELECT DISTINCT ON (idea_id, decision_epoch) id
    FROM genomai.decisions
    ORDER BY idea_id, decision_epoch, created_at ASC
);

-- Step 2: Add UNIQUE constraint
ALTER TABLE genomai.decisions
ADD CONSTRAINT decisions_idea_epoch_unique UNIQUE (idea_id, decision_epoch);

-- Add comment for documentation
COMMENT ON CONSTRAINT decisions_idea_epoch_unique ON genomai.decisions IS
    'Ensures only one decision per (idea_id, decision_epoch) combination. Part of idempotency guard.';
