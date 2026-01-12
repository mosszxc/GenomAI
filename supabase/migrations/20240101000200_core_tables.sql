-- Migration: 002_core_tables.sql
-- Task: #7 - Создание core identity tables
-- Description: creatives и ideas - основные сущности системы
-- Based on: DATA_SCHEMAS.md

-- ============================================
-- Creatives Table
-- ============================================

CREATE TABLE IF NOT EXISTS creatives (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_url         text NOT NULL,
  tracker_id        text NOT NULL,
  created_at        timestamp NOT NULL DEFAULT now(),
  source_type       text NOT NULL CHECK (source_type IN ('system', 'user')),
  status            text
);

-- Indexes for creatives
CREATE INDEX IF NOT EXISTS idx_creatives_tracker_id 
ON creatives(tracker_id);

CREATE INDEX IF NOT EXISTS idx_creatives_created_at 
ON creatives(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_creatives_source_type 
ON creatives(source_type);

-- Comments
COMMENT ON TABLE creatives IS 'Source of truth for creatives. Mutable table.';
COMMENT ON COLUMN creatives.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN creatives.video_url IS 'URL to the creative video';
COMMENT ON COLUMN creatives.tracker_id IS 'Keitaro tracker ID for this creative';
COMMENT ON COLUMN creatives.created_at IS 'Timestamp when creative was registered';
COMMENT ON COLUMN creatives.source_type IS 'Source of creative: system or user';
COMMENT ON COLUMN creatives.status IS 'Current status of creative (e.g., registered, processing, active)';

-- ============================================
-- Ideas Table
-- ============================================

CREATE TABLE IF NOT EXISTS ideas (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_hash    text NOT NULL UNIQUE,
  cluster_id        uuid,
  created_at        timestamp NOT NULL DEFAULT now(),
  status            text
);

-- Indexes for ideas
CREATE INDEX IF NOT EXISTS idx_ideas_canonical_hash 
ON ideas(canonical_hash);

CREATE INDEX IF NOT EXISTS idx_ideas_cluster_id 
ON ideas(cluster_id) 
WHERE cluster_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ideas_created_at 
ON ideas(created_at DESC);

-- Comments
COMMENT ON TABLE ideas IS 'Abstract ideas (canonical entities). Mutable table.';
COMMENT ON COLUMN ideas.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN ideas.canonical_hash IS 'Unique hash identifying the canonical idea';
COMMENT ON COLUMN ideas.cluster_id IS 'ID of the cluster this idea belongs to';
COMMENT ON COLUMN ideas.created_at IS 'Timestamp when idea was created';
COMMENT ON COLUMN ideas.status IS 'Current status of idea';

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'creatives'
  ) THEN
    RAISE EXCEPTION 'Table creatives was not created successfully';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'ideas'
  ) THEN
    RAISE EXCEPTION 'Table ideas was not created successfully';
  END IF;
END $$;

