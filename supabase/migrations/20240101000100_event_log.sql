-- Migration: 001_event_log.sql
-- Task: #6 - Создание таблицы event_log
-- Description: Append-only таблица для логирования всех событий системы
-- Based on: DATA_SCHEMAS.md, EVENT_MODEL.md

-- ============================================
-- Event Log Table (Append-Only)
-- ============================================

CREATE TABLE IF NOT EXISTS event_log (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type        text NOT NULL,
  entity_type       text,
  entity_id         uuid,
  payload           jsonb,
  occurred_at       timestamp NOT NULL DEFAULT now(),
  idempotency_key   text
);

-- ============================================
-- Indexes for Performance
-- ============================================

-- Index for event type queries (most common)
CREATE INDEX IF NOT EXISTS idx_event_log_event_type_occurred_at 
ON event_log(event_type, occurred_at DESC);

-- Index for entity lookups
CREATE INDEX IF NOT EXISTS idx_event_log_entity 
ON event_log(entity_type, entity_id) 
WHERE entity_type IS NOT NULL AND entity_id IS NOT NULL;

-- Index for idempotency checks (unique constraint would be better, but idempotency_key can be null)
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_log_idempotency_key 
ON event_log(idempotency_key) 
WHERE idempotency_key IS NOT NULL;

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_event_log_occurred_at 
ON event_log(occurred_at DESC);

-- ============================================
-- Constraints & Rules
-- ============================================

-- Add comment to table
COMMENT ON TABLE event_log IS 'Append-only event log. Records are never updated or deleted.';

-- Add comments to columns
COMMENT ON COLUMN event_log.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN event_log.event_type IS 'Type of event (e.g., CreativeReferenceReceived, DecisionMade)';
COMMENT ON COLUMN event_log.entity_type IS 'Type of entity this event relates to (e.g., creative, idea, decision)';
COMMENT ON COLUMN event_log.entity_id IS 'ID of the entity this event relates to';
COMMENT ON COLUMN event_log.payload IS 'Event-specific data as JSON';
COMMENT ON COLUMN event_log.occurred_at IS 'Timestamp when event occurred (UTC)';
COMMENT ON COLUMN event_log.idempotency_key IS 'Key for deduplication. Must be unique if provided.';

-- ============================================
-- Security: Prevent UPDATE and DELETE
-- ============================================

-- Create a function to prevent updates
CREATE OR REPLACE FUNCTION prevent_event_log_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'UPDATE on event_log is forbidden. This is an append-only table.';
END;
$$ LANGUAGE plpgsql;

-- Create a function to prevent deletes
CREATE OR REPLACE FUNCTION prevent_event_log_delete()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'DELETE on event_log is forbidden. This is an append-only table.';
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trigger_prevent_event_log_update ON event_log;
CREATE TRIGGER trigger_prevent_event_log_update
  BEFORE UPDATE ON event_log
  FOR EACH ROW
  EXECUTE FUNCTION prevent_event_log_update();

DROP TRIGGER IF EXISTS trigger_prevent_event_log_delete ON event_log;
CREATE TRIGGER trigger_prevent_event_log_delete
  BEFORE DELETE ON event_log
  FOR EACH ROW
  EXECUTE FUNCTION prevent_event_log_delete();

-- ============================================
-- Verification
-- ============================================

-- Verify table was created
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'event_log'
  ) THEN
    RAISE EXCEPTION 'Table event_log was not created successfully';
  END IF;
END $$;

