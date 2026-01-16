-- 049_auth_password_verification.sql
-- Issue #750: Username/password auth with Telegram verification
-- Добавляет password_hash в buyers и таблицу verification_codes

-- 1. Добавить password_hash в buyers
ALTER TABLE genomai.buyers
ADD COLUMN IF NOT EXISTS password_hash TEXT;

COMMENT ON COLUMN genomai.buyers.password_hash IS 'bcrypt hash of user password';

-- 2. Создать индекс по telegram_username для быстрого поиска при логине
CREATE INDEX IF NOT EXISTS idx_buyers_telegram_username
ON genomai.buyers(telegram_username) WHERE telegram_username IS NOT NULL;

-- 3. Таблица верификационных кодов
CREATE TABLE IF NOT EXISTS genomai.verification_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_username TEXT NOT NULL,          -- @username без @
  telegram_id BIGINT,                       -- заполняется когда юзер пишет /start боту
  code TEXT,                                -- 6-значный код (генерируется при /start)
  type TEXT NOT NULL CHECK (type IN ('registration', 'password_reset')),
  expires_at TIMESTAMPTZ NOT NULL,
  verified_at TIMESTAMPTZ,                  -- когда код был подтверждён
  created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE genomai.verification_codes IS 'Temporary verification codes for registration and password reset';
COMMENT ON COLUMN genomai.verification_codes.telegram_username IS 'Telegram username without @ prefix';
COMMENT ON COLUMN genomai.verification_codes.telegram_id IS 'Filled when user sends /start to bot';
COMMENT ON COLUMN genomai.verification_codes.code IS '6-digit verification code, generated when user writes /start';

-- Indexes for verification_codes
CREATE INDEX IF NOT EXISTS idx_verification_codes_username_type
ON genomai.verification_codes(telegram_username, type)
WHERE verified_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_verification_codes_expires
ON genomai.verification_codes(expires_at)
WHERE verified_at IS NULL;

-- 4. Очистить существующих пользователей (система ещё не в проде)
-- ВНИМАНИЕ: раскомментировать для продакшена если нужно
-- TRUNCATE genomai.buyers CASCADE;

-- 5. Функция для автоматической очистки устаревших кодов
CREATE OR REPLACE FUNCTION genomai.cleanup_expired_verification_codes()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM genomai.verification_codes
  WHERE expires_at < now() - INTERVAL '1 day';

  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION genomai.cleanup_expired_verification_codes IS 'Delete verification codes expired more than 1 day ago';
