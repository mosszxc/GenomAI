-- Migration: 018_exploration
-- Purpose: Add exploration_log table for tracking exploration vs exploitation
-- Issue: #123

-- Create exploration_log table
CREATE TABLE IF NOT EXISTS genomai.exploration_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What was explored
    exploration_type TEXT NOT NULL CHECK (exploration_type IN (
        'new_avatar',      -- Avatar with few samples
        'new_component',   -- Component with few samples
        'mutation',        -- Variation of known working element
        'random'           -- Pure random exploration
    )),

    -- Context
    idea_id UUID REFERENCES genomai.ideas(id),
    avatar_id UUID REFERENCES genomai.avatars(id),
    component_type TEXT,
    component_value TEXT,
    geo TEXT,

    -- Decision context
    exploration_score NUMERIC(5,4),  -- Thompson sampling score that won
    exploitation_score NUMERIC(5,4), -- Best known option score
    sample_size_at_decision INT,     -- How many samples existed when decided

    -- Outcome (filled after result)
    was_successful BOOLEAN,
    outcome_cpa NUMERIC(10,2),
    outcome_spend NUMERIC(10,2),
    outcome_revenue NUMERIC(10,2),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    outcome_recorded_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_exploration_log_type
ON genomai.exploration_log(exploration_type);

CREATE INDEX IF NOT EXISTS idx_exploration_log_avatar
ON genomai.exploration_log(avatar_id);

CREATE INDEX IF NOT EXISTS idx_exploration_log_created
ON genomai.exploration_log(created_at);

CREATE INDEX IF NOT EXISTS idx_exploration_log_success
ON genomai.exploration_log(was_successful) WHERE was_successful IS NOT NULL;

-- Comments
COMMENT ON TABLE genomai.exploration_log IS
'Tracks exploration decisions for the 25% exploration budget. Used to measure exploration effectiveness.';

COMMENT ON COLUMN genomai.exploration_log.exploration_type IS
'Type of exploration: new_avatar (unfamiliar avatar), new_component (untested component), mutation (variant), random';

COMMENT ON COLUMN genomai.exploration_log.sample_size_at_decision IS
'Number of samples for this option when exploration decision was made. Lower = more uncertain = higher exploration priority.';
