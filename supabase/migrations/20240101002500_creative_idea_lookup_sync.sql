-- Migration: 025_creative_idea_lookup_sync
-- Issue: #267 - Auto-register Keitaro tracker_id in creative_idea_lookup
-- Description: Fix view to use direct idea_id from creatives with fallback to computed
--
-- Problem: creative_idea_lookup view only computed idea_id via get_idea_id_by_creative(),
-- ignoring the direct creatives.idea_id column. This caused IDEA_NOT_FOUND errors in
-- MetricsProcessingWorkflow for creatives that had idea_id set directly.
--
-- Solution: Update view to use COALESCE(c.idea_id, computed_idea_id)

-- Drop and recreate the view with COALESCE
CREATE OR REPLACE VIEW genomai.creative_idea_lookup AS
SELECT
    c.id AS creative_id,
    c.tracker_id,
    COALESCE(c.idea_id, genomai.get_idea_id_by_creative(c.id)) AS idea_id
FROM genomai.creatives c;

COMMENT ON VIEW genomai.creative_idea_lookup IS 'Issue #267: Links tracker_id to idea_id. Uses direct idea_id from creatives with fallback to computed via decomposed_creatives';
