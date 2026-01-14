-- Migration: 044_historical_import_queue
-- Description: Create historical_import_queue table (was missing CREATE TABLE)
-- Issue: #587
--
-- Note: Table exists in production but CREATE TABLE migration was never committed.
-- This ensures the table is created on fresh database setups.

CREATE TABLE IF NOT EXISTS genomai.historical_import_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id TEXT UNIQUE NOT NULL,
  video_url TEXT,
  buyer_id UUID REFERENCES genomai.buyers(id),
  status TEXT DEFAULT 'pending_video'
    CHECK (status IN ('pending_video', 'ready', 'processing', 'completed', 'failed', 'expired')),
  metrics JSONB DEFAULT '{}',
  keitaro_source TEXT,
  date_from DATE,
  date_to DATE,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_historical_queue_buyer ON genomai.historical_import_queue(buyer_id);
CREATE INDEX IF NOT EXISTS idx_historical_queue_status ON genomai.historical_import_queue(status);

COMMENT ON TABLE genomai.historical_import_queue IS 'Queue for historical campaign imports from Keitaro';
COMMENT ON COLUMN genomai.historical_import_queue.status IS
'Status: pending_video (awaiting video URL), ready (has video), processing, completed, failed, expired (no video after 7+ days)';
