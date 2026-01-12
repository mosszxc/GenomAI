-- Migration: 024_hypothesis_buyer_id_trigger
-- Issue: #226 - Hypothesis Factory не копирует buyer_id из creative
-- Description: Auto-populate buyer_id in hypotheses from creative chain

-- Function: lookup buyer_id from creative through idea → decomposed_creative → creative chain
CREATE OR REPLACE FUNCTION genomai.get_buyer_id_for_idea(p_idea_id UUID)
RETURNS UUID AS $$
DECLARE
  v_buyer_id UUID;
BEGIN
  SELECT c.buyer_id::uuid INTO v_buyer_id
  FROM genomai.creatives c
  JOIN genomai.decomposed_creatives dc ON c.id = dc.creative_id
  WHERE dc.idea_id = p_idea_id
  LIMIT 1;

  RETURN v_buyer_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- Trigger function: auto-populate buyer_id on hypothesis insert
CREATE OR REPLACE FUNCTION genomai.hypothesis_set_buyer_id()
RETURNS TRIGGER AS $$
BEGIN
  -- Only set buyer_id if not already provided
  IF NEW.buyer_id IS NULL AND NEW.idea_id IS NOT NULL THEN
    NEW.buyer_id := genomai.get_buyer_id_for_idea(NEW.idea_id);
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on hypotheses table
DROP TRIGGER IF EXISTS trg_hypothesis_set_buyer_id ON genomai.hypotheses;

CREATE TRIGGER trg_hypothesis_set_buyer_id
  BEFORE INSERT ON genomai.hypotheses
  FOR EACH ROW
  EXECUTE FUNCTION genomai.hypothesis_set_buyer_id();

-- Comments
COMMENT ON FUNCTION genomai.get_buyer_id_for_idea IS 'Lookups buyer_id from creative through idea → decomposed_creative → creative chain';
COMMENT ON FUNCTION genomai.hypothesis_set_buyer_id IS 'Trigger function: auto-populates buyer_id on hypothesis insert from creative chain';
COMMENT ON TRIGGER trg_hypothesis_set_buyer_id ON genomai.hypotheses IS 'Issue #226: Auto-populate buyer_id from creative chain';

-- Backfill existing hypotheses (one-time)
UPDATE genomai.hypotheses h
SET buyer_id = genomai.get_buyer_id_for_idea(h.idea_id)
WHERE h.buyer_id IS NULL
  AND genomai.get_buyer_id_for_idea(h.idea_id) IS NOT NULL;
