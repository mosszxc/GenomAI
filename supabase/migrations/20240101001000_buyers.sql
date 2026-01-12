-- 010_buyers.sql
-- Buyer registration and state management

-- Таблица зарегистрированных баеров
CREATE TABLE IF NOT EXISTS genomai.buyers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id TEXT UNIQUE NOT NULL,      -- telegram user_id
  telegram_username TEXT,                 -- @username (может быть null)
  name TEXT NOT NULL,                     -- имя баера
  geo TEXT,                               -- основное гео (DE, US, FR, etc)
  vertical TEXT,                          -- направление нутры
  status TEXT DEFAULT 'active',           -- active, inactive, blocked
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE genomai.buyers IS 'Registered buyers who can submit creatives';
COMMENT ON COLUMN genomai.buyers.vertical IS 'Nutra vertical: weight_loss, potency, joints, diabetes, beauty, heart, vision, detox, other';

-- Таблица состояний для multi-step онбординга
CREATE TABLE IF NOT EXISTS genomai.buyer_states (
  telegram_id TEXT PRIMARY KEY,
  state TEXT DEFAULT 'idle',              -- idle, awaiting_name, awaiting_geo, awaiting_vertical
  context JSONB DEFAULT '{}',             -- {name: "Иван", geo: "DE"}
  updated_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE genomai.buyer_states IS 'Temporary state storage for multi-step buyer onboarding';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_buyers_telegram
ON genomai.buyers(telegram_id);

CREATE INDEX IF NOT EXISTS idx_buyers_geo_vertical
ON genomai.buyers(geo, vertical);

CREATE INDEX IF NOT EXISTS idx_buyers_status
ON genomai.buyers(status) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_buyer_states_updated
ON genomai.buyer_states(updated_at);

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION genomai.update_buyers_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для автообновления updated_at
DROP TRIGGER IF EXISTS trigger_buyers_updated ON genomai.buyers;
CREATE TRIGGER trigger_buyers_updated
  BEFORE UPDATE ON genomai.buyers
  FOR EACH ROW
  EXECUTE FUNCTION genomai.update_buyers_timestamp();

DROP TRIGGER IF EXISTS trigger_buyer_states_updated ON genomai.buyer_states;
CREATE TRIGGER trigger_buyer_states_updated
  BEFORE UPDATE ON genomai.buyer_states
  FOR EACH ROW
  EXECUTE FUNCTION genomai.update_buyers_timestamp();
