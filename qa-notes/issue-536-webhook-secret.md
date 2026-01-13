# Issue #536: Telegram Webhook Signature Verification

## Что изменено
- Добавлена верификация `X-Telegram-Bot-Api-Secret-Token` заголовка в webhook endpoint
- Используется `secrets.compare_digest()` для защиты от timing attacks
- Если `TELEGRAM_WEBHOOK_SECRET` не задан - верификация пропускается (обратная совместимость)
- HTTPException 401 при отсутствии/неверном токене

## Затронутые файлы
- `decision-engine-service/src/routes/telegram.py`

## Test
```bash
cd decision-engine-service && uv run pytest tests/unit/test_webhook_secret.py -v
```

## Manual verification
```bash
# С правильным секретом - должен вернуть {"ok": true}
curl -X POST localhost:10000/webhook/telegram \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: test_secret_123" \
  -d '{"update_id": 123}'

# Без секрета - должен вернуть 401
curl -X POST localhost:10000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"update_id": 123}'

# С неверным секретом - должен вернуть 401
curl -X POST localhost:10000/webhook/telegram \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: wrong_secret" \
  -d '{"update_id": 123}'
```

## Настройка в production
1. Сгенерировать секрет: `openssl rand -hex 32`
2. Добавить в Render env: `TELEGRAM_WEBHOOK_SECRET=<generated_secret>`
3. Обновить webhook в Telegram:
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://genomai.onrender.com/webhook/telegram" \
  -d "secret_token=<generated_secret>"
```
