-- Migration: 040_creative_failed_status
-- Issue: #472 - Stuck Creatives — отсутствует состояние 'failed'
-- Description: Add error column to creatives table and retry_count for recovery

-- Add error column to store failure reason
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS error TEXT;

-- Add retry_count for failed creatives recovery
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0;

-- Add failed_at timestamp
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;

-- Index for finding failed creatives for retry
CREATE INDEX IF NOT EXISTS idx_creatives_failed_status
ON genomai.creatives (status, retry_count, failed_at)
WHERE status = 'failed';

-- Comment on columns
COMMENT ON COLUMN genomai.creatives.error IS 'Error message when status=failed';
COMMENT ON COLUMN genomai.creatives.retry_count IS 'Number of retry attempts for failed creatives';
COMMENT ON COLUMN genomai.creatives.failed_at IS 'Timestamp when creative entered failed status';
