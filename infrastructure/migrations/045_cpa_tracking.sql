-- Migration: 045_cpa_tracking
-- Purpose: Add CPA tracking and weekly trend snapshots for module_bank
-- Issue: #601

-- ============================================================================
-- module_bank - add CPA tracking columns
-- ============================================================================

-- Add total_conversions column for CPA calculation
ALTER TABLE genomai.module_bank
ADD COLUMN IF NOT EXISTS total_conversions INT DEFAULT 0;

-- Add generated avg_cpa column (spend / conversions)
-- Note: PostgreSQL 12+ supports ADD COLUMN with GENERATED ALWAYS AS
ALTER TABLE genomai.module_bank
ADD COLUMN IF NOT EXISTS avg_cpa NUMERIC GENERATED ALWAYS AS (
    CASE WHEN total_conversions > 0 THEN total_spend / total_conversions ELSE NULL END
) STORED;

-- Index for CPA-based selection
CREATE INDEX IF NOT EXISTS idx_module_bank_avg_cpa
ON genomai.module_bank(module_type, avg_cpa ASC NULLS LAST)
WHERE status = 'active' AND avg_cpa IS NOT NULL;

-- ============================================================================
-- module_weekly_snapshots - weekly performance snapshots for trend tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS genomai.module_weekly_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to module
    module_id UUID NOT NULL REFERENCES genomai.module_bank(id) ON DELETE CASCADE,

    -- Week identifier (ISO week: YYYY-WW format, e.g., "2026-02")
    week_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    -- Snapshot of metrics at end of week
    sample_size INT NOT NULL DEFAULT 0,
    win_count INT NOT NULL DEFAULT 0,
    loss_count INT NOT NULL DEFAULT 0,
    total_spend NUMERIC NOT NULL DEFAULT 0,
    total_revenue NUMERIC NOT NULL DEFAULT 0,
    total_conversions INT NOT NULL DEFAULT 0,

    -- Computed metrics
    win_rate NUMERIC GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0 END
    ) STORED,
    avg_cpa NUMERIC GENERATED ALWAYS AS (
        CASE WHEN total_conversions > 0 THEN total_spend / total_conversions ELSE NULL END
    ) STORED,
    avg_roi NUMERIC GENERATED ALWAYS AS (
        CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
    ) STORED,

    -- Trend vs previous week (calculated at snapshot time)
    win_rate_trend NUMERIC,           -- (current - prev) / prev, NULL if first week
    cpa_trend NUMERIC,                -- (current - prev) / prev, negative is better
    roi_trend NUMERIC,                -- (current - prev) / prev

    -- Deltas (absolute change from previous week)
    sample_size_delta INT DEFAULT 0,
    win_count_delta INT DEFAULT 0,
    spend_delta NUMERIC DEFAULT 0,
    conversions_delta INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (module_id, week_id)
);

-- Index for fetching recent snapshots for a module
CREATE INDEX IF NOT EXISTS idx_module_snapshots_module_week
ON genomai.module_weekly_snapshots(module_id, week_start DESC);

-- Index for finding snapshots by week
CREATE INDEX IF NOT EXISTS idx_module_snapshots_week
ON genomai.module_weekly_snapshots(week_id);

-- Index for trend analysis (modules with improving/declining CPA)
CREATE INDEX IF NOT EXISTS idx_module_snapshots_cpa_trend
ON genomai.module_weekly_snapshots(cpa_trend)
WHERE cpa_trend IS NOT NULL;

-- ============================================================================
-- Enable RLS
-- ============================================================================

ALTER TABLE genomai.module_weekly_snapshots ENABLE ROW LEVEL SECURITY;

-- Service role policy (full access)
CREATE POLICY "service_role_full_access_module_snapshots" ON genomai.module_weekly_snapshots
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- Helper function: Get trend for last N weeks
-- ============================================================================

CREATE OR REPLACE FUNCTION genomai.get_module_trend(
    p_module_id UUID,
    p_weeks INT DEFAULT 4
)
RETURNS TABLE (
    week_id TEXT,
    week_start DATE,
    avg_cpa NUMERIC,
    win_rate NUMERIC,
    cpa_trend NUMERIC,
    win_rate_trend NUMERIC,
    sample_size INT,
    sample_size_delta INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.week_id,
        s.week_start,
        s.avg_cpa,
        s.win_rate,
        s.cpa_trend,
        s.win_rate_trend,
        s.sample_size,
        s.sample_size_delta
    FROM genomai.module_weekly_snapshots s
    WHERE s.module_id = p_module_id
    ORDER BY s.week_start DESC
    LIMIT p_weeks;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE genomai.module_weekly_snapshots IS 'Weekly performance snapshots for module trend tracking';
COMMENT ON COLUMN genomai.module_bank.total_conversions IS 'Total conversions attributed to this module';
COMMENT ON COLUMN genomai.module_bank.avg_cpa IS 'Average CPA (Cost Per Acquisition) - generated from spend/conversions';
COMMENT ON COLUMN genomai.module_weekly_snapshots.week_id IS 'ISO week identifier (YYYY-WW format)';
COMMENT ON COLUMN genomai.module_weekly_snapshots.cpa_trend IS 'Relative change in CPA vs previous week: (current - prev) / prev. Negative is better.';
COMMENT ON FUNCTION genomai.get_module_trend IS 'Get trend data for a module over last N weeks';
