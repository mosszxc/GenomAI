-- Migration: 048_transcripts_revert_to_pascal_case.sql
-- Issue: #724 - Revert snake_case columns back to PascalCase
-- Reason: pg_cron worker, trigger function, and n8n workflows depend on PascalCase column names

-- Revert snake_case columns back to PascalCase
ALTER TABLE genomai.transcripts
  RENAME COLUMN status TO "Status";

ALTER TABLE genomai.transcripts
  RENAME COLUMN name TO "Name";

ALTER TABLE genomai.transcripts
  RENAME COLUMN translate_text TO "TranslateText";

ALTER TABLE genomai.transcripts
  RENAME COLUMN translate_status TO "TranslateStatus";

ALTER TABLE genomai.transcripts
  RENAME COLUMN convert_status TO "ConvertStatus";

ALTER TABLE genomai.transcripts
  RENAME COLUMN audio_id TO "AudioID";

ALTER TABLE genomai.transcripts
  RENAME COLUMN video_id TO "VideoID";

ALTER TABLE genomai.transcripts
  RENAME COLUMN transcribe_status TO "TranscribeStatus";

ALTER TABLE genomai.transcripts
  RENAME COLUMN render_status TO "RenderStatus";

ALTER TABLE genomai.transcripts
  RENAME COLUMN last_webhook_at TO "LastWebhookAt";

-- Verification
DO $$
BEGIN
  -- Verify PascalCase columns exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'transcripts'
    AND column_name = 'Status'
  ) THEN
    RAISE EXCEPTION 'Column Status was not restored';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'genomai'
    AND table_name = 'transcripts'
    AND column_name = 'ConvertStatus'
  ) THEN
    RAISE EXCEPTION 'Column ConvertStatus was not restored';
  END IF;
END $$;
