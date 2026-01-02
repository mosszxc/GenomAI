-- Migration: 023_historical_queue_expired_status
-- Description: Add 'expired' status for campaigns stuck in pending_video too long
-- Issue: #200

-- Add 'expired' to allowed statuses
ALTER TABLE genomai.historical_import_queue
DROP CONSTRAINT IF EXISTS historical_import_queue_status_check;

ALTER TABLE genomai.historical_import_queue
ADD CONSTRAINT historical_import_queue_status_check
CHECK (status IN ('pending_video', 'ready', 'processing', 'completed', 'failed', 'expired'));

-- Add comment explaining statuses
COMMENT ON COLUMN genomai.historical_import_queue.status IS
'Status: pending_video (awaiting video URL), ready (has video), processing, completed, failed, expired (no video after 7+ days)';
