-- Migration: 047_transcripts_snake_case.sql
-- Issue: #710 - Rename PascalCase columns to snake_case
-- Description: Standardize column names in transcripts table

-- Rename PascalCase columns to snake_case
ALTER TABLE genomai.transcripts
  RENAME COLUMN "Status" TO status;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "Name" TO name;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "TranslateText" TO translate_text;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "TranslateStatus" TO translate_status;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "ConvertStatus" TO convert_status;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "AudioID" TO audio_id;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "VideoID" TO video_id;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "TranscribeStatus" TO transcribe_status;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "RenderStatus" TO render_status;

ALTER TABLE genomai.transcripts
  RENAME COLUMN "LastWebhookAt" TO last_webhook_at;

-- Add comments for documentation
COMMENT ON COLUMN genomai.transcripts.status IS 'Overall transcript status (queued, finish, error)';
COMMENT ON COLUMN genomai.transcripts.name IS 'Transcript name for pg_cron identification';
COMMENT ON COLUMN genomai.transcripts.translate_text IS 'Translated transcript text';
COMMENT ON COLUMN genomai.transcripts.translate_status IS 'Translation status (queued, finish, error)';
COMMENT ON COLUMN genomai.transcripts.convert_status IS 'MP4→MP3 conversion status (queued, finish, error)';
COMMENT ON COLUMN genomai.transcripts.audio_id IS 'Google Drive audio file ID after conversion';
COMMENT ON COLUMN genomai.transcripts.video_id IS 'Google Drive video file ID';
COMMENT ON COLUMN genomai.transcripts.transcribe_status IS 'AssemblyAI transcription status (queued, finish, error)';
COMMENT ON COLUMN genomai.transcripts.render_status IS 'Render status';
COMMENT ON COLUMN genomai.transcripts.last_webhook_at IS 'Last webhook callback timestamp';

-- Verification
DO $$
BEGIN
  -- Verify columns exist with new names
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'transcripts'
    AND column_name = 'status'
  ) THEN
    RAISE EXCEPTION 'Column status was not renamed successfully';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'transcripts'
    AND column_name = 'convert_status'
  ) THEN
    RAISE EXCEPTION 'Column convert_status was not renamed successfully';
  END IF;
END $$;
