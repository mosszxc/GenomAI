-- Migration: 029_component_learnings_origin
-- Purpose: Add origin tracking to component_learnings for cross-segment transfer and external injection
-- Issue: Inspiration System

-- ============================================================================
-- COMPONENT LEARNINGS ORIGIN TRACKING
-- ============================================================================

-- Add origin columns to component_learnings
ALTER TABLE genomai.component_learnings
ADD COLUMN IF NOT EXISTS origin_type TEXT DEFAULT 'organic'
    CHECK (origin_type IN ('organic', 'cross_transfer', 'external_injection', 'manual'));

ALTER TABLE genomai.component_learnings
ADD COLUMN IF NOT EXISTS origin_source_id UUID;

ALTER TABLE genomai.component_learnings
ADD COLUMN IF NOT EXISTS origin_segment JSONB;

ALTER TABLE genomai.component_learnings
ADD COLUMN IF NOT EXISTS injected_at TIMESTAMPTZ;

-- Comments
COMMENT ON COLUMN genomai.component_learnings.origin_type IS
'Source of component: organic (from creatives), cross_transfer (from another segment), external_injection (from spy tools), manual (admin input)';

COMMENT ON COLUMN genomai.component_learnings.origin_source_id IS
'Reference to external_inspirations.id if origin_type = external_injection';

COMMENT ON COLUMN genomai.component_learnings.origin_segment IS
'Source segment {avatar_id, geo} if origin_type = cross_transfer';

COMMENT ON COLUMN genomai.component_learnings.injected_at IS
'Timestamp when component was injected (for cross_transfer or external_injection)';

-- Index for finding injected components
CREATE INDEX IF NOT EXISTS idx_component_learnings_origin
ON genomai.component_learnings(origin_type) WHERE origin_type != 'organic';

CREATE INDEX IF NOT EXISTS idx_component_learnings_injected
ON genomai.component_learnings(injected_at) WHERE injected_at IS NOT NULL;


-- ============================================================================
-- EXPLORATION LOG UPDATE
-- ============================================================================

-- Drop existing CHECK constraint on exploration_type
ALTER TABLE genomai.exploration_log
DROP CONSTRAINT IF EXISTS exploration_log_exploration_type_check;

-- Add new CHECK constraint with additional types
ALTER TABLE genomai.exploration_log
ADD CONSTRAINT exploration_log_exploration_type_check
CHECK (exploration_type IN (
    'new_avatar',
    'new_component',
    'mutation',
    'random',
    'cross_transfer',      -- NEW: from another segment
    'external_injection'   -- NEW: from spy tools
));

-- Comment update
COMMENT ON COLUMN genomai.exploration_log.exploration_type IS
'Type of exploration: new_avatar, new_component, mutation, random, cross_transfer (from another segment), external_injection (from spy tools)';
