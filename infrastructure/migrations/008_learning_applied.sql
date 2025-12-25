-- 008_learning_applied.sql
-- Add learning_applied flag to outcome_aggregates for Learning Loop (Step 08)

ALTER TABLE genomai.outcome_aggregates
ADD COLUMN IF NOT EXISTS learning_applied BOOLEAN DEFAULT false;

-- Partial index for efficient lookup of unapplied outcomes
CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_learning_pending
ON genomai.outcome_aggregates(learning_applied)
WHERE learning_applied = false;

COMMENT ON COLUMN genomai.outcome_aggregates.learning_applied IS 'True when outcome has been processed by Learning Loop (prevents duplicate learning)';
