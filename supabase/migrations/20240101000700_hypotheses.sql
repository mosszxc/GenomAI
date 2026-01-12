-- Migration: 007_hypotheses.sql
-- Task: #7 - Создание таблиц для hypotheses и deliveries
-- Description: hypotheses и deliveries - генерация и доставка гипотез
-- Based on: DATA_SCHEMAS.md

-- ============================================
-- Hypotheses Table
-- ============================================

CREATE TABLE IF NOT EXISTS hypotheses (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id           uuid NOT NULL,
  transcript_text   text NOT NULL,
  version           int NOT NULL,
  created_at        timestamp NOT NULL DEFAULT now(),
  status            text
);

-- Indexes for hypotheses
CREATE INDEX IF NOT EXISTS idx_hypotheses_idea_id 
ON hypotheses(idea_id);

CREATE INDEX IF NOT EXISTS idx_hypotheses_idea_version 
ON hypotheses(idea_id, version DESC);

CREATE INDEX IF NOT EXISTS idx_hypotheses_created_at 
ON hypotheses(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_hypotheses_status 
ON hypotheses(status) 
WHERE status IS NOT NULL;

-- Comments
COMMENT ON TABLE hypotheses IS 'Generated hypotheses (transcripts) for ideas.';
COMMENT ON COLUMN hypotheses.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN hypotheses.idea_id IS 'Reference to idea';
COMMENT ON COLUMN hypotheses.transcript_text IS 'Generated transcript text';
COMMENT ON COLUMN hypotheses.version IS 'Version number of hypothesis';
COMMENT ON COLUMN hypotheses.created_at IS 'Timestamp when hypothesis was created';
COMMENT ON COLUMN hypotheses.status IS 'Status of hypothesis (e.g., generated, delivered, active)';

-- ============================================
-- Deliveries Table
-- ============================================

CREATE TABLE IF NOT EXISTS deliveries (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hypothesis_id     uuid NOT NULL,
  channel           text,
  delivered_at      timestamp NOT NULL DEFAULT now(),
  delivery_status   text
);

-- Indexes for deliveries
CREATE INDEX IF NOT EXISTS idx_deliveries_hypothesis_id 
ON deliveries(hypothesis_id);

CREATE INDEX IF NOT EXISTS idx_deliveries_channel 
ON deliveries(channel) 
WHERE channel IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_deliveries_delivered_at 
ON deliveries(delivered_at DESC);

CREATE INDEX IF NOT EXISTS idx_deliveries_status 
ON deliveries(delivery_status) 
WHERE delivery_status IS NOT NULL;

-- Comments
COMMENT ON TABLE deliveries IS 'Delivery records for hypotheses.';
COMMENT ON COLUMN deliveries.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN deliveries.hypothesis_id IS 'Reference to hypothesis';
COMMENT ON COLUMN deliveries.channel IS 'Delivery channel (e.g., telegram)';
COMMENT ON COLUMN deliveries.delivered_at IS 'Timestamp when delivery occurred';
COMMENT ON COLUMN deliveries.delivery_status IS 'Status of delivery (e.g., sent, failed, pending)';

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'hypotheses'
  ) THEN
    RAISE EXCEPTION 'Table hypotheses was not created successfully';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'deliveries'
  ) THEN
    RAISE EXCEPTION 'Table deliveries was not created successfully';
  END IF;
END $$;

