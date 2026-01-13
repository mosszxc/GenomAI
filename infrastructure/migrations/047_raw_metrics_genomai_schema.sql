-- Migration: 047_raw_metrics_genomai_schema.sql
-- Issue: #706 - raw_metrics_current returns 404 from /health/metrics
--
-- Problem: PostgREST schema cache may not see the table, causing 404 errors.
--
-- Solution: Create RPC function for reliable metrics staleness check.

-- ============================================
-- Ensure table exists in genomai schema
-- ============================================

CREATE TABLE IF NOT EXISTS genomai.raw_metrics_current (
    tracker_id  TEXT NOT NULL,
    date        DATE NOT NULL,
    metrics     JSONB NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tracker_id, date)
);

-- Index for staleness check (ORDER BY updated_at DESC)
CREATE INDEX IF NOT EXISTS idx_raw_metrics_current_updated_at
ON genomai.raw_metrics_current(updated_at DESC);

-- Comments
COMMENT ON TABLE genomai.raw_metrics_current IS 'Current raw metrics from Keitaro (mutable, upsert).';


-- ============================================
-- RPC function for metrics staleness check
-- ============================================

CREATE OR REPLACE FUNCTION genomai.get_metrics_staleness()
RETURNS TABLE (
    latest_updated_at TIMESTAMPTZ,
    staleness_minutes NUMERIC,
    is_stale BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rmc.updated_at AS latest_updated_at,
        EXTRACT(EPOCH FROM (NOW() - rmc.updated_at)) / 60 AS staleness_minutes,
        EXTRACT(EPOCH FROM (NOW() - rmc.updated_at)) / 60 > 30 AS is_stale
    FROM genomai.raw_metrics_current rmc
    ORDER BY rmc.updated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION genomai.get_metrics_staleness() IS 'Returns metrics staleness info for health check. Issue #706.';


-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.routines
        WHERE routine_schema = 'genomai'
        AND routine_name = 'get_metrics_staleness'
    ) THEN
        RAISE EXCEPTION 'Function genomai.get_metrics_staleness was not created successfully';
    END IF;
END $$;
