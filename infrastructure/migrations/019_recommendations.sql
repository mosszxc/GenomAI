-- Migration: 019_recommendations.sql
-- Issue: #124
-- Purpose: Create recommendations table for buyer guidance

-- Recommendations table
CREATE TABLE IF NOT EXISTS genomai.recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    buyer_id UUID REFERENCES genomai.buyers(id),
    avatar_id UUID REFERENCES genomai.avatars(id),
    geo TEXT,
    vertical TEXT,

    -- Recommendation content
    recommended_components JSONB NOT NULL,  -- {hook_mechanism: "confession", angle_type: "pain", ...}
    mode TEXT NOT NULL CHECK (mode IN ('exploitation', 'exploration')),
    exploration_type TEXT,  -- new_component, new_avatar, mutation, random (when mode=exploration)
    description TEXT,  -- Human-readable description for buyer

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'executed', 'expired')),

    -- Outcome tracking
    creative_id UUID REFERENCES genomai.creatives(id),  -- When buyer creates creative
    was_successful BOOLEAN,  -- Outcome after learning
    outcome_cpa NUMERIC(10,2),
    outcome_spend NUMERIC(10,2),
    outcome_revenue NUMERIC(10,2),

    -- Confidence scores at generation time
    confidence_scores JSONB,  -- {hook_mechanism: 0.85, angle_type: 0.72, ...}
    avg_confidence NUMERIC(5,4),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    outcome_recorded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_recommendations_buyer_id ON genomai.recommendations(buyer_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_avatar_id ON genomai.recommendations(avatar_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON genomai.recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recommendations_mode ON genomai.recommendations(mode);
CREATE INDEX IF NOT EXISTS idx_recommendations_created_at ON genomai.recommendations(created_at DESC);

-- Comments
COMMENT ON TABLE genomai.recommendations IS 'Recommendations for buyers: which components to use in creatives';
COMMENT ON COLUMN genomai.recommendations.mode IS 'exploitation = use proven components, exploration = try undersampled';
COMMENT ON COLUMN genomai.recommendations.exploration_type IS 'Type of exploration: new_component, new_avatar, mutation, random';
COMMENT ON COLUMN genomai.recommendations.recommended_components IS 'JSONB with component_type: component_value pairs';
