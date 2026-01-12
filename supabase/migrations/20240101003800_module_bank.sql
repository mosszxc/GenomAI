-- Migration: 038_module_bank
-- Purpose: Create tables for Modular Creative System
-- - module_bank: stores Hook, Promise, Proof modules with metrics
-- - module_compatibility: pairwise compatibility scores
-- - hypotheses extension: module references and review_status

-- ============================================================================
-- module_bank - stores reusable creative modules
-- ============================================================================
CREATE TABLE IF NOT EXISTS genomai.module_bank (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Module identity
    module_type TEXT NOT NULL CHECK (module_type IN ('hook', 'promise', 'proof')),
    module_key TEXT NOT NULL,  -- SHA256 hash for deduplication

    -- Content
    content JSONB NOT NULL,    -- Extracted fields from decomposed payload
    text_content TEXT,         -- Human-readable text (for hooks)

    -- Source tracking
    source_creative_id UUID REFERENCES genomai.creatives(id),
    source_decomposed_id UUID REFERENCES genomai.decomposed_creatives(id),

    -- Context
    vertical TEXT,
    geo TEXT,
    avatar_id UUID REFERENCES genomai.avatars(id),

    -- Metrics (same pattern as component_learnings)
    sample_size INT DEFAULT 0,
    win_count INT DEFAULT 0,
    loss_count INT DEFAULT 0,
    total_spend NUMERIC DEFAULT 0,
    total_revenue NUMERIC DEFAULT 0,

    -- Generated columns
    win_rate NUMERIC GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0 END
    ) STORED,
    avg_roi NUMERIC GENERATED ALWAYS AS (
        CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
    ) STORED,

    -- State
    status TEXT DEFAULT 'emerging' CHECK (status IN ('active', 'emerging', 'fatigued', 'dead')),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (module_type, module_key)
);

-- Index for prioritized selection by win_rate
CREATE INDEX IF NOT EXISTS idx_module_bank_type_win_rate
ON genomai.module_bank(module_type, win_rate DESC)
WHERE status = 'active';

-- Index for exploration queries (low sample_size)
CREATE INDEX IF NOT EXISTS idx_module_bank_exploration
ON genomai.module_bank(module_type, sample_size)
WHERE sample_size < 5;

-- Index for source tracking
CREATE INDEX IF NOT EXISTS idx_module_bank_source_creative
ON genomai.module_bank(source_creative_id);

-- ============================================================================
-- module_compatibility - pairwise compatibility scores
-- ============================================================================
CREATE TABLE IF NOT EXISTS genomai.module_compatibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    module_a_id UUID NOT NULL REFERENCES genomai.module_bank(id) ON DELETE CASCADE,
    module_b_id UUID NOT NULL REFERENCES genomai.module_bank(id) ON DELETE CASCADE,

    sample_size INT DEFAULT 0,
    win_count INT DEFAULT 0,

    compatibility_score NUMERIC GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0.5 END
    ) STORED,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (module_a_id, module_b_id),
    CHECK (module_a_id < module_b_id)  -- Canonical ordering to avoid duplicates
);

-- Index for compatibility lookups
CREATE INDEX IF NOT EXISTS idx_module_compatibility_a
ON genomai.module_compatibility(module_a_id);

CREATE INDEX IF NOT EXISTS idx_module_compatibility_b
ON genomai.module_compatibility(module_b_id);

-- ============================================================================
-- hypotheses extension - add module references and review_status
-- ============================================================================
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS hook_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS promise_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS proof_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS generation_mode TEXT DEFAULT 'reformulation'
    CHECK (generation_mode IN ('reformulation', 'modular'));

ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT 'auto_approved'
    CHECK (review_status IN ('pending_review', 'approved', 'rejected', 'auto_approved'));

-- Index for pending reviews
CREATE INDEX IF NOT EXISTS idx_hypotheses_pending_review
ON genomai.hypotheses(review_status)
WHERE review_status = 'pending_review';

-- Index for modular hypotheses
CREATE INDEX IF NOT EXISTS idx_hypotheses_generation_mode
ON genomai.hypotheses(generation_mode)
WHERE generation_mode = 'modular';

-- ============================================================================
-- Enable RLS
-- ============================================================================
ALTER TABLE genomai.module_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE genomai.module_compatibility ENABLE ROW LEVEL SECURITY;

-- Service role policy (full access)
CREATE POLICY "service_role_full_access_module_bank" ON genomai.module_bank
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_module_compatibility" ON genomai.module_compatibility
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE genomai.module_bank IS 'Reusable creative modules (Hook, Promise, Proof) with performance metrics';
COMMENT ON TABLE genomai.module_compatibility IS 'Pairwise compatibility scores for module combinations';
COMMENT ON COLUMN genomai.hypotheses.generation_mode IS 'How hypothesis was generated: reformulation (from idea) or modular (from module_bank)';
COMMENT ON COLUMN genomai.hypotheses.review_status IS 'Human review status for modular hypotheses';
