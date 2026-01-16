# Issue #751 - Bot Refactoring to Notification-Only Role

## Что изменено

### Удалено из telegram.py (3168 → 462 строк)
- 20 команд удалено: `/stats`, `/genome`, `/confidence`, `/trends`, `/drift`, `/correlations`, `/recommend`, `/meta`, `/simulate`, `/buyers`, `/activity`, `/decisions`, `/creatives`, `/status`, `/errors`, `/pending`, `/approve`, `/reject`, `/knowledge`, `/feedback`
- Обработчики: `handle_video_url`, `handle_document_upload`, `handle_callback_query`, `handle_user_message`
- Все вспомогательные функции для удалённых команд

### Оставлено в telegram.py
- `/start` - редирект на Cockpit для регистрации
- `/help` - минимальная справка
- Все неизвестные команды игнорируются молча (200 OK, без ответа)

### Удалено из temporal/activities/telegram.py
- `send_hypothesis_to_telegram`
- `send_status_notification`

### Обновлено в creative_pipeline.py
- Удалён Step 7: Telegram Delivery
- Удалены progress notifications (notify_progress)

## Поведение

1. `/start` → отправляет сообщение с кнопкой для перехода на Cockpit
2. `/help` → отправляет минимальную справку
3. Любая другая команда → 200 OK, без ответа (молча игнорируется)
4. Callback queries → молча игнорируются
5. Документы, видео, обычные сообщения → молча игнорируются

## Test

```bash
# Проверка что webhook endpoint отвечает
curl -sf -X POST http://localhost:10000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1, "message": {"message_id": 1, "chat": {"id": 123}, "from": {"id": 456}, "text": "/unknown"}}' \
  && echo "OK: webhook accepts requests"
```

## Связанные issues
- Зависит от #750 (auth endpoints для верификации)
