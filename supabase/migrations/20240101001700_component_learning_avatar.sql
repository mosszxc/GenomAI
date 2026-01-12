-- Migration: 017_component_learning_avatar
-- Purpose: Add avatar_id support to component_learnings for per-avatar learning
-- Issue: #122

-- Add avatar_id column (NULL = global learning)
ALTER TABLE genomai.component_learnings
ADD COLUMN IF NOT EXISTS avatar_id UUID REFERENCES genomai.avatars(id);

-- Create index for faster avatar lookups
CREATE INDEX IF NOT EXISTS idx_component_learnings_avatar_id
ON genomai.component_learnings(avatar_id);

-- Create unique constraint for component+avatar combination
-- This ensures one row per (component_type, component_value, geo, avatar_id)
ALTER TABLE genomai.component_learnings
DROP CONSTRAINT IF EXISTS component_learnings_unique_combo;

ALTER TABLE genomai.component_learnings
ADD CONSTRAINT component_learnings_unique_combo
UNIQUE (component_type, component_value, geo, avatar_id);

-- Comment
COMMENT ON COLUMN genomai.component_learnings.avatar_id IS
'Avatar ID for per-avatar learning. NULL means global learning across all avatars.';
