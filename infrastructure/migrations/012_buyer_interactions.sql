-- Migration: 012_buyer_interactions
-- Description: Add table for logging all buyer-bot interactions (chat history)
-- Date: 2025-12-25

-- buyer_interactions: полная история взаимодействий с байерами
CREATE TABLE IF NOT EXISTS genomai.buyer_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id TEXT NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),  -- in = от байера, out = от бота
  message_type TEXT NOT NULL CHECK (message_type IN ('text', 'video', 'photo', 'document', 'command', 'callback', 'system')),
  content TEXT,  -- текст сообщения или описание действия
  context JSONB DEFAULT '{}',  -- доп. данные: callback_data, file_id, video_url и т.д.
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_buyer_interactions_telegram_id
  ON genomai.buyer_interactions(telegram_id);

CREATE INDEX IF NOT EXISTS idx_buyer_interactions_created_at
  ON genomai.buyer_interactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_buyer_interactions_telegram_created
  ON genomai.buyer_interactions(telegram_id, created_at DESC);

-- Комментарии
COMMENT ON TABLE genomai.buyer_interactions IS 'Append-only log of all buyer-bot interactions. Used for chat history and analytics.';
COMMENT ON COLUMN genomai.buyer_interactions.direction IS 'in = message from buyer, out = message from bot';
COMMENT ON COLUMN genomai.buyer_interactions.message_type IS 'Type: text, video, photo, document, command, callback, system';
COMMENT ON COLUMN genomai.buyer_interactions.context IS 'Additional data: file_id, callback_data, creative_id, etc.';
