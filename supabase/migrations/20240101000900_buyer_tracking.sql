-- 009_buyer_tracking.sql
-- Buyer creative tracking and component learning

-- Добавить source_type в creatives
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'system';

COMMENT ON COLUMN genomai.creatives.source_type IS 'system = ingested automatically, user = registered by buyer';

-- Добавить tracking_status для отслеживания состояния теста
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS tracking_status TEXT DEFAULT 'pending';

COMMENT ON COLUMN genomai.creatives.tracking_status IS 'pending → tracking → concluded';

-- Threshold config (бюджет на тест)
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS test_budget NUMERIC DEFAULT 15;

COMMENT ON COLUMN genomai.creatives.test_budget IS 'Budget threshold to conclude test ($15 default)';

-- Buyer ID (telegram user_id)
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS buyer_id TEXT;

COMMENT ON COLUMN genomai.creatives.buyer_id IS 'Telegram user_id of the buyer who registered this creative';

-- Результат теста
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS test_result TEXT;

COMMENT ON COLUMN genomai.creatives.test_result IS 'win = ROI > 0, loss = ROI <= 0, inconclusive = no signal';

-- Время завершения теста
ALTER TABLE genomai.creatives
ADD COLUMN IF NOT EXISTS concluded_at TIMESTAMPTZ;

-- Component learnings - агрегированная статистика по компонентам
CREATE TABLE IF NOT EXISTS genomai.component_learnings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Идентификация компонента
  component_type TEXT NOT NULL,  -- hook_type, angle_type, cta_type, opening_type, etc.
  component_value TEXT NOT NULL, -- problem-solution, fear, free-trial, etc.
  geo TEXT,                      -- nullable, для гео-специфичных паттернов

  -- Статистика
  sample_size INT DEFAULT 0,
  win_count INT DEFAULT 0,
  loss_count INT DEFAULT 0,
  total_spend NUMERIC DEFAULT 0,
  total_revenue NUMERIC DEFAULT 0,

  -- Вычисляемые метрики
  win_rate NUMERIC GENERATED ALWAYS AS (
    CASE WHEN sample_size > 0 THEN win_count::NUMERIC / sample_size ELSE 0 END
  ) STORED,
  avg_roi NUMERIC GENERATED ALWAYS AS (
    CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
  ) STORED,

  -- Метаданные
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE (component_type, component_value, geo)
);

COMMENT ON TABLE genomai.component_learnings IS 'Aggregated performance stats per idea component';

-- Index для быстрого поиска по buyer
CREATE INDEX IF NOT EXISTS idx_creatives_buyer
ON genomai.creatives(buyer_id, tracking_status);

-- Index для поиска активных тестов
CREATE INDEX IF NOT EXISTS idx_creatives_tracking
ON genomai.creatives(tracking_status) WHERE tracking_status = 'tracking';

-- Index для component_learnings по win_rate
CREATE INDEX IF NOT EXISTS idx_component_learnings_performance
ON genomai.component_learnings(component_type, win_rate DESC) WHERE sample_size >= 5;

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION genomai.update_component_learnings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автообновления updated_at
DROP TRIGGER IF EXISTS trigger_component_learnings_updated ON genomai.component_learnings;
CREATE TRIGGER trigger_component_learnings_updated
  BEFORE UPDATE ON genomai.component_learnings
  FOR EACH ROW
  EXECUTE FUNCTION genomai.update_component_learnings_timestamp();
