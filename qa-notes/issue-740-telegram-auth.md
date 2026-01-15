# Issue #740: Telegram Login Widget Auth Endpoint

## Что изменено
- Добавлен `src/routes/auth.py` с endpoint POST `/api/auth/telegram`
- Верификация hash (HMAC-SHA256 с SHA256(BOT_TOKEN) как ключом)
- Проверка auth_date (не старше 24ч)
- Поиск buyer по telegram_id в Supabase
- Генерация access_token для найденного buyer

## Файлы
- `decision-engine-service/src/routes/auth.py` — новый endpoint
- `decision-engine-service/main.py` — регистрация router
- `tests/unit/test_auth.py` — unit тесты

## API

### POST /api/auth/telegram

**Request:**
```json
{
  "id": 123456789,
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "photo_url": "https://t.me/i/userpic/320/abc.jpg",
  "auth_date": 1736956800,
  "hash": "abc123..."
}
```

**Response (success):**
```json
{
  "success": true,
  "access_token": "buyer-id:timestamp:signature",
  "buyer_id": "uuid",
  "name": "John"
}
```

**Response (error):**
```json
{
  "success": false,
  "error": "Buyer not found. Please register first via Telegram bot."
}
```

## Test

```bash
# Проверка что endpoint отвечает (ожидаем 422 без body)
curl -sf -X POST localhost:10000/api/auth/telegram \
  -H "Content-Type: application/json" \
  -d '{}' 2>&1 | grep -q "422\|field required\|validation" && echo "OK: endpoint exists" || echo "FAIL: endpoint missing"
```

## Security Notes
- Hash верифицируется по алгоритму Telegram Login Widget
- auth_date проверяется на свежесть (24ч)
- Без валидного hash авторизация невозможна
- Требуется существующий buyer в базе
