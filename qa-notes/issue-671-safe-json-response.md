# Issue #671: Safe JSON Response

## Что изменено

- Добавлена helper функция `safe_json_response()` для безопасного парсинга HTTP ответов
- Функция проверяет HTTP статус и обрабатывает ошибки JSON парсинга
- Исправлены все `.json()` вызовы без проверки статуса в telegram.py:
  - `/stats` команда (3 вызова)
  - `/buyers` команда (2 вызова)
  - `/activity` команда (2 вызова)
  - `/chat` команда (2 вызова)
  - `/decisions` команда (1 вызов)
  - `/creatives` команда (1 вызов)
  - `/errors` команда (1 вызов)
  - `/knowledge` команда (1 вызов)
  - `get_buyer_name` функция (1 вызов)
  - `handle_document_upload` (1 вызов - Telegram API)
  - `handle_video_url` (1 вызов)
  - `send_telegram_message` (1 вызов - Telegram API)
  - `send_telegram_photo` (1 вызов - Telegram API)
  - `telegram_webhook_status` endpoint (1 вызов - Telegram API)

## Почему это важно

При недоступности Supabase (503) или Telegram API (500), сервер возвращал HTML вместо JSON.
Вызов `.json()` без проверки приводил к JSONDecodeError и падению команд.

## Test

```bash
grep -c "safe_json_response" decision-engine-service/src/routes/telegram.py | grep -q "^1[5-9]$\|^2[0-9]$" && echo "OK: 15+ uses of safe_json_response" || echo "FAIL: expected 15+ uses"
```
