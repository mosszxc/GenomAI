-- Migration: 020_reminder_log
-- Description: Таблица для трекинга напоминаний о pending_video кампаниях
-- Issue: #164

-- Таблица для трекинга напоминаний о pending_video
CREATE TABLE IF NOT EXISTS genomai.reminder_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id UUID NOT NULL REFERENCES genomai.buyers(id),
  reminder_type TEXT NOT NULL CHECK (reminder_type IN ('first', 'repeat', 'last', 'expired')),
  pending_count INTEGER NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс для быстрого поиска последнего напоминания
CREATE INDEX IF NOT EXISTS idx_reminder_log_buyer_sent
  ON genomai.reminder_log(buyer_id, sent_at DESC);

COMMENT ON TABLE genomai.reminder_log IS 'Лог отправленных напоминаний о pending_video кампаниях';
