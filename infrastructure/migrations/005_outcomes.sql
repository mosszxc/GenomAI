-- Migration: 005_outcomes.sql
-- Task: #7 - Создание таблицы outcome_aggregates
-- Description: Immutable outcome aggregates для learning
-- Based on: DATA_SCHEMAS.md, STORAGE_MODEL.md

-- ============================================
-- Outcome Aggregates Table (Immutable)
-- ============================================

CREATE TABLE IF NOT EXISTS outcome_aggregates (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  creative_id       uuid NOT NULL,
  window_id         text,
  window_start      date NOT NULL,
  window_end         date NOT NULL,
  impressions       int,
  conversions       int,
  spend             numeric,
  cpa               numeric,
  trend             text,
  volatility        numeric,
  environment_ctx   jsonb,
  origin_type       text NOT NULL CHECK (origin_type IN ('system', 'user')),
  decision_id       uuid,
  created_at        timestamp NOT NULL DEFAULT now(),
  UNIQUE (creative_id, window_start, window_end),
  CHECK (
    (origin_type = 'system' AND decision_id IS NOT NULL)
    OR
    (origin_type = 'user')
  )
);

-- Indexes for outcome_aggregates
CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_creative_id 
ON outcome_aggregates(creative_id);

CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_window 
ON outcome_aggregates(creative_id, window_start, window_end);

CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_window_id 
ON outcome_aggregates(window_id) 
WHERE window_id IS NOT NULL;

-- Partial index for system outcomes (for joins with decisions)
CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_decision_id 
ON outcome_aggregates(decision_id) 
WHERE origin_type = 'system' AND decision_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_origin_type 
ON outcome_aggregates(origin_type);

CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_created_at 
ON outcome_aggregates(created_at DESC);

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_environment_ctx 
ON outcome_aggregates USING GIN (environment_ctx) 
WHERE environment_ctx IS NOT NULL;

-- Comments
COMMENT ON TABLE outcome_aggregates IS 'Immutable outcome aggregates. Used for learning.';
COMMENT ON COLUMN outcome_aggregates.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN outcome_aggregates.creative_id IS 'Reference to creative';
COMMENT ON COLUMN outcome_aggregates.window_id IS 'Optional window identifier (e.g., D1_D3, D1_D7)';
COMMENT ON COLUMN outcome_aggregates.window_start IS 'Start date of outcome window';
COMMENT ON COLUMN outcome_aggregates.window_end IS 'End date of outcome window';
COMMENT ON COLUMN outcome_aggregates.impressions IS 'Total impressions in window';
COMMENT ON COLUMN outcome_aggregates.conversions IS 'Total conversions in window';
COMMENT ON COLUMN outcome_aggregates.spend IS 'Total spend in window';
COMMENT ON COLUMN outcome_aggregates.cpa IS 'CPA_window - primary success metric for MVP';
COMMENT ON COLUMN outcome_aggregates.trend IS 'Trend direction (e.g., up, down, stable)';
COMMENT ON COLUMN outcome_aggregates.volatility IS 'Volatility metric';
COMMENT ON COLUMN outcome_aggregates.environment_ctx IS 'Environment context as JSON';
COMMENT ON COLUMN outcome_aggregates.origin_type IS 'Origin: system (requires decision_id) or user';
COMMENT ON COLUMN outcome_aggregates.decision_id IS 'Reference to decision (required for system outcomes)';
COMMENT ON COLUMN outcome_aggregates.created_at IS 'Timestamp when outcome was created';

-- ============================================
-- Security: Prevent UPDATE and DELETE
-- ============================================

-- Create a function to prevent updates
CREATE OR REPLACE FUNCTION prevent_outcome_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'UPDATE on outcome_aggregates is forbidden. This is an immutable table.';
END;
$$ LANGUAGE plpgsql;

-- Create a function to prevent deletes
CREATE OR REPLACE FUNCTION prevent_outcome_delete()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'DELETE on outcome_aggregates is forbidden. This is an immutable table.';
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trigger_prevent_outcome_update ON outcome_aggregates;
CREATE TRIGGER trigger_prevent_outcome_update
  BEFORE UPDATE ON outcome_aggregates
  FOR EACH ROW
  EXECUTE FUNCTION prevent_outcome_update();

DROP TRIGGER IF EXISTS trigger_prevent_outcome_delete ON outcome_aggregates;
CREATE TRIGGER trigger_prevent_outcome_delete
  BEFORE DELETE ON outcome_aggregates
  FOR EACH ROW
  EXECUTE FUNCTION prevent_outcome_delete();

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'outcome_aggregates'
  ) THEN
    RAISE EXCEPTION 'Table outcome_aggregates was not created successfully';
  END IF;

  -- Verify CHECK constraint exists
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_schema = 'public' 
    AND table_name = 'outcome_aggregates'
    AND constraint_type = 'CHECK'
  ) THEN
    RAISE WARNING 'CHECK constraint on outcome_aggregates may not be properly set';
  END IF;
END $$;

