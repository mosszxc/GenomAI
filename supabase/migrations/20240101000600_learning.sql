-- Migration: 006_learning.sql
-- Task: #7 - Создание таблиц для learning memory
-- Description: idea_confidence_versions и fatigue_state_versions - versioned state для learning
-- Based on: DATA_SCHEMAS.md, LEARNING_MEMORY_POLICY.md

-- ============================================
-- Idea Confidence Versions (Versioned State)
-- ============================================

CREATE TABLE IF NOT EXISTS idea_confidence_versions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id           uuid NOT NULL,
  confidence_value  numeric NOT NULL,
  version           int NOT NULL,
  updated_at        timestamp NOT NULL DEFAULT now(),
  source_outcome_id uuid NOT NULL,
  UNIQUE (idea_id, version),
  CHECK (source_outcome_id IS NOT NULL)
);

-- Indexes for idea_confidence_versions
CREATE INDEX IF NOT EXISTS idx_idea_confidence_versions_idea_id 
ON idea_confidence_versions(idea_id);

CREATE INDEX IF NOT EXISTS idx_idea_confidence_versions_idea_version 
ON idea_confidence_versions(idea_id, version DESC);

-- Index for provenance tracking (learning from outcomes)
CREATE INDEX IF NOT EXISTS idx_idea_confidence_versions_source_outcome 
ON idea_confidence_versions(source_outcome_id);

-- Comments
COMMENT ON TABLE idea_confidence_versions IS 'Versioned confidence state. Learning only from outcomes.';
COMMENT ON COLUMN idea_confidence_versions.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN idea_confidence_versions.idea_id IS 'Reference to idea';
COMMENT ON COLUMN idea_confidence_versions.confidence_value IS 'Confidence value (numeric)';
COMMENT ON COLUMN idea_confidence_versions.version IS 'Version number (increments with each learning update)';
COMMENT ON COLUMN idea_confidence_versions.updated_at IS 'Timestamp when confidence was updated';
COMMENT ON COLUMN idea_confidence_versions.source_outcome_id IS 'Reference to outcome that triggered this learning (required, NOT NULL)';

-- ============================================
-- Fatigue State Versions (Versioned State)
-- ============================================

CREATE TABLE IF NOT EXISTS fatigue_state_versions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id           uuid NOT NULL,
  fatigue_value     numeric NOT NULL,
  version           int NOT NULL,
  updated_at        timestamp NOT NULL DEFAULT now(),
  source_outcome_id uuid NOT NULL,
  UNIQUE (idea_id, version),
  CHECK (source_outcome_id IS NOT NULL)
);

-- Indexes for fatigue_state_versions
CREATE INDEX IF NOT EXISTS idx_fatigue_state_versions_idea_id 
ON fatigue_state_versions(idea_id);

CREATE INDEX IF NOT EXISTS idx_fatigue_state_versions_idea_version 
ON fatigue_state_versions(idea_id, version DESC);

-- Index for provenance tracking (learning from outcomes)
CREATE INDEX IF NOT EXISTS idx_fatigue_state_versions_source_outcome 
ON fatigue_state_versions(source_outcome_id);

-- Comments
COMMENT ON TABLE fatigue_state_versions IS 'Versioned fatigue state. Learning only from outcomes.';
COMMENT ON COLUMN fatigue_state_versions.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN fatigue_state_versions.idea_id IS 'Reference to idea';
COMMENT ON COLUMN fatigue_state_versions.fatigue_value IS 'Fatigue value (numeric)';
COMMENT ON COLUMN fatigue_state_versions.version IS 'Version number (increments with each learning update)';
COMMENT ON COLUMN fatigue_state_versions.updated_at IS 'Timestamp when fatigue was updated';
COMMENT ON COLUMN fatigue_state_versions.source_outcome_id IS 'Reference to outcome that triggered this learning (required, NOT NULL)';

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'idea_confidence_versions'
  ) THEN
    RAISE EXCEPTION 'Table idea_confidence_versions was not created successfully';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'fatigue_state_versions'
  ) THEN
    RAISE EXCEPTION 'Table fatigue_state_versions was not created successfully';
  END IF;

  -- Verify CHECK constraints exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_schema = 'public' 
    AND table_name = 'idea_confidence_versions'
    AND constraint_type = 'CHECK'
  ) THEN
    RAISE WARNING 'CHECK constraint on idea_confidence_versions may not be properly set';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_schema = 'public' 
    AND table_name = 'fatigue_state_versions'
    AND constraint_type = 'CHECK'
  ) THEN
    RAISE WARNING 'CHECK constraint on fatigue_state_versions may not be properly set';
  END IF;
END $$;

