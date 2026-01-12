-- Migration: 004_metrics.sql
-- Task: #7 - Создание таблиц для метрик
-- Description: raw_metrics_current (mutable) и daily_metrics_snapshot (append-only)
-- Based on: DATA_SCHEMAS.md, STORAGE_MODEL.md

-- ============================================
-- Raw Metrics Current (Mutable)
-- ============================================

CREATE TABLE IF NOT EXISTS raw_metrics_current (
  creative_id       uuid PRIMARY KEY,
  impressions       int,
  clicks            int,
  conversions       int,
  spend             numeric,
  updated_at        timestamp NOT NULL DEFAULT now()
);

-- Indexes for raw_metrics_current
CREATE INDEX IF NOT EXISTS idx_raw_metrics_current_updated_at 
ON raw_metrics_current(updated_at DESC);

-- Comments
COMMENT ON TABLE raw_metrics_current IS 'Current raw metrics (mutable). NOT used for learning.';
COMMENT ON COLUMN raw_metrics_current.creative_id IS 'Primary key, reference to creative';
COMMENT ON COLUMN raw_metrics_current.impressions IS 'Number of impressions';
COMMENT ON COLUMN raw_metrics_current.clicks IS 'Number of clicks';
COMMENT ON COLUMN raw_metrics_current.conversions IS 'Number of conversions';
COMMENT ON COLUMN raw_metrics_current.spend IS 'Total spend';
COMMENT ON COLUMN raw_metrics_current.updated_at IS 'Timestamp when metrics were last updated';

-- ============================================
-- Daily Metrics Snapshot (Append-Only)
-- ============================================

CREATE TABLE IF NOT EXISTS daily_metrics_snapshot (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  creative_id       uuid NOT NULL,
  snapshot_date     date NOT NULL,
  impressions_day  int,
  clicks_day        int,
  conversions_day   int,
  spend_day         numeric,
  created_at        timestamp NOT NULL DEFAULT now(),
  UNIQUE (creative_id, snapshot_date)
);

-- Indexes for daily_metrics_snapshot
CREATE INDEX IF NOT EXISTS idx_daily_metrics_snapshot_creative_id 
ON daily_metrics_snapshot(creative_id);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_snapshot_date 
ON daily_metrics_snapshot(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_snapshot_creative_date 
ON daily_metrics_snapshot(creative_id, snapshot_date DESC);

-- Comments
COMMENT ON TABLE daily_metrics_snapshot IS 'Daily snapshots of metrics (append-only, immutable).';
COMMENT ON COLUMN daily_metrics_snapshot.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN daily_metrics_snapshot.creative_id IS 'Reference to creative';
COMMENT ON COLUMN daily_metrics_snapshot.snapshot_date IS 'Date of the snapshot';
COMMENT ON COLUMN daily_metrics_snapshot.impressions_day IS 'Impressions for this day';
COMMENT ON COLUMN daily_metrics_snapshot.clicks_day IS 'Clicks for this day';
COMMENT ON COLUMN daily_metrics_snapshot.conversions_day IS 'Conversions for this day';
COMMENT ON COLUMN daily_metrics_snapshot.spend_day IS 'Spend for this day';
COMMENT ON COLUMN daily_metrics_snapshot.created_at IS 'Timestamp when snapshot was created';

-- ============================================
-- Security: Prevent UPDATE and DELETE on snapshots
-- ============================================

-- Create a function to prevent updates
CREATE OR REPLACE FUNCTION prevent_snapshot_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'UPDATE on daily_metrics_snapshot is forbidden. This is an append-only table.';
END;
$$ LANGUAGE plpgsql;

-- Create a function to prevent deletes
CREATE OR REPLACE FUNCTION prevent_snapshot_delete()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'DELETE on daily_metrics_snapshot is forbidden. This is an append-only table.';
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trigger_prevent_snapshot_update ON daily_metrics_snapshot;
CREATE TRIGGER trigger_prevent_snapshot_update
  BEFORE UPDATE ON daily_metrics_snapshot
  FOR EACH ROW
  EXECUTE FUNCTION prevent_snapshot_update();

DROP TRIGGER IF EXISTS trigger_prevent_snapshot_delete ON daily_metrics_snapshot;
CREATE TRIGGER trigger_prevent_snapshot_delete
  BEFORE DELETE ON daily_metrics_snapshot
  FOR EACH ROW
  EXECUTE FUNCTION prevent_snapshot_delete();

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'raw_metrics_current'
  ) THEN
    RAISE EXCEPTION 'Table raw_metrics_current was not created successfully';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'daily_metrics_snapshot'
  ) THEN
    RAISE EXCEPTION 'Table daily_metrics_snapshot was not created successfully';
  END IF;
END $$;

