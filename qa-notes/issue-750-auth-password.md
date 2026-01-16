# Issue #750: Username/Password Auth with Telegram Verification

## Что изменено

### Новые файлы
- `infrastructure/migrations/049_auth_password_verification.sql` - миграция для password_hash и verification_codes

### Изменённые файлы
- `decision-engine-service/src/routes/auth.py` - полностью переписан с новыми эндпоинтами
- `decision-engine-service/src/routes/telegram.py` - обновлён /start для отправки кодов верификации
- `decision-engine-service/requirements.txt` - добавлен bcrypt

### Новые API эндпоинты

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/api/auth/register/init` | Начать регистрацию по telegram_username |
| POST | `/api/auth/register/verify` | Подтвердить код и создать аккаунт |
| POST | `/api/auth/login` | Вход по username/password |
| POST | `/api/auth/reset-password/init` | Начать сброс пароля |
| POST | `/api/auth/reset-password/verify` | Подтвердить код и сменить пароль |

### Удалённые эндпоинты
- `POST /api/auth/telegram` (Telegram Login Widget)

## Флоу регистрации

1. Frontend: POST `/api/auth/register/init` с `{telegram_username: "user"}`
2. Backend возвращает `{verification_id: "uuid", message: "Send /start to bot"}`
3. Пользователь пишет /start боту @UniAiHelper_bot
4. Бот находит pending verification, генерирует код, отправляет пользователю
5. Frontend: POST `/api/auth/register/verify` с `{verification_id, code, password}`
6. Backend создаёт аккаунт и возвращает access_token

## Database Changes

```sql
-- Новое поле в buyers
ALTER TABLE genomai.buyers ADD COLUMN password_hash TEXT;

-- Новая таблица
CREATE TABLE genomai.verification_codes (
  id UUID PRIMARY KEY,
  telegram_username TEXT NOT NULL,
  telegram_id BIGINT,
  code TEXT,
  type TEXT NOT NULL, -- 'registration' | 'password_reset'
  expires_at TIMESTAMPTZ NOT NULL,
  verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Test

```bash
curl -sf localhost:10000/api/auth/register/init \
  -H "Content-Type: application/json" \
  -d '{"telegram_username": "testuser"}' \
  | grep -q "verification_id" && echo "OK: register/init works"
```

## Manual Testing

1. Применить миграцию:
```bash
psql $DATABASE_URL -f infrastructure/migrations/049_auth_password_verification.sql
```

2. Запустить сервер:
```bash
make up
```

3. Тест регистрации:
```bash
# 1. Инициировать регистрацию
curl -X POST localhost:10000/api/auth/register/init \
  -H "Content-Type: application/json" \
  -d '{"telegram_username": "your_tg_username"}'

# 2. Написать /start боту @UniAiHelper_bot
# 3. Получить код в Telegram

# 4. Завершить регистрацию
curl -X POST localhost:10000/api/auth/register/verify \
  -H "Content-Type: application/json" \
  -d '{"verification_id": "UUID_FROM_STEP_1", "code": "123456", "password": "mypassword"}'
```

4. Тест логина:
```bash
curl -X POST localhost:10000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_username": "your_tg_username", "password": "mypassword"}'
```
