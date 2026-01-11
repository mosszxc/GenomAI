-- Migration: 032_hypothesis_retry.sql
-- Issue: #313 - Failed hypothesis retry mechanism
-- Description: Add retry tracking columns for hypothesis delivery

-- Add retry_count to track delivery attempts
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0;

-- Add last_retry_at to prevent rapid retries
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMPTZ;

-- Add last_error to store failure reason
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS last_error TEXT;

-- Index for finding failed hypotheses to retry
CREATE INDEX IF NOT EXISTS idx_hypotheses_status_retry
ON genomai.hypotheses(status, retry_count)
WHERE status = 'failed' AND retry_count < 3;

-- Comments
COMMENT ON COLUMN genomai.hypotheses.retry_count IS 'Number of delivery retry attempts. Max 3.';
COMMENT ON COLUMN genomai.hypotheses.last_retry_at IS 'Timestamp of last retry attempt';
COMMENT ON COLUMN genomai.hypotheses.last_error IS 'Last delivery error message';

-- Verification
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'hypotheses'
    AND column_name = 'retry_count'
  ) THEN
    RAISE EXCEPTION 'Column retry_count was not created';
  END IF;
END $$;
