# Супер простая цепочка проверки Webhook'ов

**Версия:** v1.0  
**Назначение:** Простая проверка webhook'ов в одну команду

## 🚀 Быстрая проверка

### Вариант 1: По Workflow ID

```bash
node tests/scripts/test_webhook_simple.cjs dvZvUUmhtPzYOK7X
```

**Что делает:**
1. Получает workflow через API
2. Находит webhook URL
3. Отправляет тестовый payload
4. Показывает результат

### Вариант 2: По Webhook URL

```bash
node tests/scripts/test_webhook_simple.cjs https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X/ingest/creative
```

**Что делает:**
1. Отправляет тестовый payload на webhook URL
2. Показывает результат

## 📋 Тестовый Payload

По умолчанию отправляется:

```json
{
  "video_url": "https://example.com/test/video/123",
  "tracker_id": "KT-TEST-123",
  "source_type": "user"
}
```

## ✅ Пример вывода

```
============================================================
[HEADER] GenomAI — Simple Webhook Test
============================================================

[INFO] Получение webhook URL из workflow: dvZvUUmhtPzYOK7X
[PASS] Webhook URL найден: https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X/ingest/creative

[INFO] Тестирование webhook: https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X/ingest/creative
[INFO] Payload: {
  "video_url": "https://example.com/test/video/123",
  "tracker_id": "KT-TEST-123",
  "source_type": "user"
}

[INFO] Status Code: 200
[INFO] Response: { ... }
[PASS] ✅ Webhook работает!

============================================================
[PASS] ✅ Webhook работает корректно!
```

## 🔧 Настройка

```bash
# Обязательные (для получения workflow)
export N8N_API_KEY="your-n8n-api-key"

# Опциональные
export N8N_API_URL="https://kazamaqwe.app.n8n.cloud/api/v1"
```

## 💡 Использование в Cursor

### Просто скажи мне:

```
"Проверь webhook для workflow dvZvUUmhtPzYOK7X"
```

**Или:**

```
"Проверь webhook https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X"
```

**Я автоматически:**
1. Найду webhook URL (если указан workflow ID)
2. Отправлю тестовый payload
3. Покажу результат

## 📚 Связанные документы

- [WEBHOOK_GUIDE.md](../docs/WEBHOOK_GUIDE.md) — Полное руководство по webhook'ам
- [test_ingestion.js](./test_ingestion.js) — Расширенное тестирование ingestion webhook

