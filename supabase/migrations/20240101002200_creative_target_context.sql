-- Migration: Add target_vertical and target_geo to creatives
-- Issue: #193
-- Purpose: Store the specific vertical/geo context for each creative

ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS target_vertical TEXT,
ADD COLUMN IF NOT EXISTS target_geo TEXT;

-- Index for filtering by vertical/geo
CREATE INDEX IF NOT EXISTS idx_creatives_target
ON genomai.creatives(target_vertical, target_geo);

-- Comment
COMMENT ON COLUMN genomai.creatives.target_vertical IS 'Target vertical for this creative (from buyer.verticals[0] at registration time)';
COMMENT ON COLUMN genomai.creatives.target_geo IS 'Target geo for this creative (from buyer.geos[0] at registration time)';
