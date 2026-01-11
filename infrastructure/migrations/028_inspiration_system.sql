-- Migration: 028_inspiration_system
-- Purpose: Add staleness detection and external inspiration tables
-- Issue: Inspiration System - prevent creative degradation

-- ============================================================================
-- STALENESS DETECTION
-- ============================================================================

-- Create staleness_snapshots table
CREATE TABLE IF NOT EXISTS genomai.staleness_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Staleness metrics (0.0 - 1.0)
    diversity_score NUMERIC(5,4),           -- COUNT(DISTINCT values) / expected
    win_rate_trend NUMERIC(5,4),            -- negative = declining
    fatigue_ratio NUMERIC(5,4),             -- ideas with high fatigue / total
    days_since_new_component INT,           -- days since last new component
    exploration_success_rate NUMERIC(5,4),  -- successful explorations / total

    -- Composite score (weighted average)
    staleness_score NUMERIC(5,4),
    is_stale BOOLEAN GENERATED ALWAYS AS (staleness_score > 0.6) STORED,

    -- Context (NULL = global)
    avatar_id UUID REFERENCES genomai.avatars(id),
    geo TEXT,
    vertical TEXT,

    -- Action taken
    action_taken TEXT CHECK (action_taken IN ('none', 'cross_transfer', 'external_injection')),
    action_details JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for staleness_snapshots
CREATE INDEX IF NOT EXISTS idx_staleness_snapshots_stale
ON genomai.staleness_snapshots(is_stale, created_at);

CREATE INDEX IF NOT EXISTS idx_staleness_snapshots_segment
ON genomai.staleness_snapshots(avatar_id, geo);

CREATE INDEX IF NOT EXISTS idx_staleness_snapshots_created
ON genomai.staleness_snapshots(created_at);

-- Comments
COMMENT ON TABLE genomai.staleness_snapshots IS
'Periodic snapshots of system staleness metrics. Used to trigger inspiration injection when system becomes stale.';

COMMENT ON COLUMN genomai.staleness_snapshots.staleness_score IS
'Composite staleness score: 0.25*diversity + 0.25*win_rate_decline + 0.20*fatigue + 0.15*days_stale + 0.15*exploration_fail';

COMMENT ON COLUMN genomai.staleness_snapshots.is_stale IS
'Generated: TRUE when staleness_score > 0.6, indicating system needs external inspiration injection';


-- ============================================================================
-- EXTERNAL INSPIRATIONS
-- ============================================================================

-- Create external_inspirations table
CREATE TABLE IF NOT EXISTS genomai.external_inspirations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source
    source_type TEXT NOT NULL CHECK (source_type IN ('adheart', 'fb_spy', 'manual', 'competitor')),
    source_url TEXT,
    source_id TEXT,  -- External system ID (e.g., AdHeart ad ID)

    -- Extracted content
    raw_creative_data JSONB,      -- Original parsed data from spy tool
    extracted_components JSONB,    -- LLM-extracted components (same format as decomposed_creatives.payload)

    -- Classification
    vertical TEXT,
    geo TEXT,
    estimated_performance TEXT CHECK (estimated_performance IN ('high', 'medium', 'low', 'unknown')),

    -- Processing status
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',      -- Awaiting LLM extraction
        'extracted',    -- Components extracted, ready for injection
        'injected',     -- Components added to component_learnings
        'rejected',     -- Not suitable (duplicate, low quality, etc.)
        'expired'       -- Too old to be relevant
    )),

    -- Injection tracking
    injection_trigger TEXT,       -- What staleness signal triggered injection
    injected_components JSONB,    -- Which components were injected
    injected_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '30 days'
);

-- Indexes for external_inspirations
CREATE INDEX IF NOT EXISTS idx_external_inspirations_status
ON genomai.external_inspirations(status);

CREATE INDEX IF NOT EXISTS idx_external_inspirations_source
ON genomai.external_inspirations(source_type);

CREATE INDEX IF NOT EXISTS idx_external_inspirations_vertical_geo
ON genomai.external_inspirations(vertical, geo);

CREATE INDEX IF NOT EXISTS idx_external_inspirations_created
ON genomai.external_inspirations(created_at);

CREATE INDEX IF NOT EXISTS idx_external_inspirations_pending
ON genomai.external_inspirations(status) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_external_inspirations_extracted
ON genomai.external_inspirations(status) WHERE status = 'extracted';

-- Comments
COMMENT ON TABLE genomai.external_inspirations IS
'External creative inspirations from spy tools (AdHeart, FB Spy). LLM extracts components which are then injected into component_learnings for Thompson Sampling exploration.';

COMMENT ON COLUMN genomai.external_inspirations.source_type IS
'Source of inspiration: adheart (AdHeart spy), fb_spy (Facebook spy), manual (human input), competitor (competitor analysis)';

COMMENT ON COLUMN genomai.external_inspirations.extracted_components IS
'LLM-extracted components in same format as decomposed_creatives.payload: {deep_desire_type, primary_trigger, hook_mechanism, etc.}';

COMMENT ON COLUMN genomai.external_inspirations.status IS
'Processing status: pending → extracted → injected (or rejected/expired)';
