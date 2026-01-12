-- Migration: 003_transcription.sql
-- Task: #7 - Создание таблиц для transcription и decomposition
-- Description: transcripts и decomposed_creatives - immutable версии транскриптов и декомпозиции
-- Based on: DATA_SCHEMAS.md

-- ============================================
-- Transcripts Table (Immutable Versions)
-- ============================================

CREATE TABLE IF NOT EXISTS transcripts (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  creative_id       uuid NOT NULL,
  version           int NOT NULL,
  transcript_text   text NOT NULL,
  created_at        timestamp NOT NULL DEFAULT now(),
  UNIQUE (creative_id, version)
);

-- Indexes for transcripts
CREATE INDEX IF NOT EXISTS idx_transcripts_creative_id 
ON transcripts(creative_id);

CREATE INDEX IF NOT EXISTS idx_transcripts_creative_id_version 
ON transcripts(creative_id, version DESC);

-- Comments
COMMENT ON TABLE transcripts IS 'Immutable versions of transcripts. UPDATE is forbidden.';
COMMENT ON COLUMN transcripts.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN transcripts.creative_id IS 'Reference to creative';
COMMENT ON COLUMN transcripts.version IS 'Version number of transcript (starts at 1)';
COMMENT ON COLUMN transcripts.transcript_text IS 'Full transcript text';
COMMENT ON COLUMN transcripts.created_at IS 'Timestamp when transcript was created';

-- ============================================
-- Decomposed Creatives Table
-- ============================================

CREATE TABLE IF NOT EXISTS decomposed_creatives (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  creative_id       uuid NOT NULL,
  schema_version    text NOT NULL,
  payload           jsonb NOT NULL,
  created_at        timestamp NOT NULL DEFAULT now()
);

-- Indexes for decomposed_creatives
CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_creative_id 
ON decomposed_creatives(creative_id);

CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_schema_version 
ON decomposed_creatives(schema_version);

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_payload 
ON decomposed_creatives USING GIN (payload);

-- Comments
COMMENT ON TABLE decomposed_creatives IS 'Canonical Schema decomposition results. Immutable.';
COMMENT ON COLUMN decomposed_creatives.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN decomposed_creatives.creative_id IS 'Reference to creative';
COMMENT ON COLUMN decomposed_creatives.schema_version IS 'Version of Canonical Schema used';
COMMENT ON COLUMN decomposed_creatives.payload IS 'Decomposed data as JSON (Canonical Schema)';
COMMENT ON COLUMN decomposed_creatives.created_at IS 'Timestamp when decomposition was created';

-- ============================================
-- Security: Prevent UPDATE on transcripts
-- ============================================

-- Create a function to prevent updates
CREATE OR REPLACE FUNCTION prevent_transcripts_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'UPDATE on transcripts is forbidden. Create a new version instead.';
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_prevent_transcripts_update ON transcripts;
CREATE TRIGGER trigger_prevent_transcripts_update
  BEFORE UPDATE ON transcripts
  FOR EACH ROW
  EXECUTE FUNCTION prevent_transcripts_update();

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'transcripts'
  ) THEN
    RAISE EXCEPTION 'Table transcripts was not created successfully';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'decomposed_creatives'
  ) THEN
    RAISE EXCEPTION 'Table decomposed_creatives was not created successfully';
  END IF;
END $$;

