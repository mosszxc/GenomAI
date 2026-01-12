-- Migration: 037_transcript_assemblyai_id.sql
-- Task: #370 - Persist transcripts before decomposition
-- Description: Add AssemblyAI transcript ID column for audit trail and idempotency

-- Add AssemblyAI transcript ID column
ALTER TABLE genomai.transcripts
ADD COLUMN IF NOT EXISTS assemblyai_transcript_id TEXT;

-- Index for lookups by AssemblyAI ID (for recovery and idempotency)
CREATE INDEX IF NOT EXISTS idx_transcripts_assemblyai_id
ON genomai.transcripts(assemblyai_transcript_id)
WHERE assemblyai_transcript_id IS NOT NULL;

-- Comment
COMMENT ON COLUMN genomai.transcripts.assemblyai_transcript_id
IS 'AssemblyAI transcript ID for audit trail and idempotency checks';
