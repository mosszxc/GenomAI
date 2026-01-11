-- Migration: 026_drop_deprecated_buyer_columns.sql
-- Description: Remove deprecated geo and vertical columns from buyers table
-- These columns are replaced by geos[] and verticals[] arrays (see migration 016)

-- ============================================
-- Drop deprecated columns
-- ============================================

ALTER TABLE genomai.buyers DROP COLUMN IF EXISTS geo;
ALTER TABLE genomai.buyers DROP COLUMN IF EXISTS vertical;

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'buyers'
    AND column_name IN ('geo', 'vertical')
  ) THEN
    RAISE EXCEPTION 'Deprecated columns still exist';
  END IF;

  -- Verify arrays exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'buyers'
    AND column_name = 'geos'
  ) THEN
    RAISE EXCEPTION 'geos column does not exist';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'buyers'
    AND column_name = 'verticals'
  ) THEN
    RAISE EXCEPTION 'verticals column does not exist';
  END IF;
END $$;
