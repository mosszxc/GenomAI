# Быстрая проверка Webhook'ов

## 🚀 Одна команда

```bash
node tests/scripts/test_webhook_simple.cjs dvZvUUmhtPzYOK7X
```

**Или с прямым URL:**

```bash
node tests/scripts/test_webhook_simple.cjs https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X
```

## ⚙️ Настройка

```bash
# Обязательно (для получения workflow через API)
export N8N_API_KEY="your-n8n-api-key"

# Опционально
export N8N_API_URL="https://kazamaqwe.app.n8n.cloud/api/v1"
```

## ✅ Что делает

1. Получает workflow через API (если указан workflow ID)
2. Находит webhook URL автоматически
3. Отправляет тестовый payload:
   ```json
   {
     "video_url": "https://example.com/test/video/123",
     "tracker_id": "KT-TEST-123",
     "source_type": "user"
   }
   ```
4. Показывает результат (status code, response)

## 📋 Пример вывода

```
============================================================
[HEADER] GenomAI — Simple Webhook Test
============================================================

[INFO] Получение webhook URL из workflow: dvZvUUmhtPzYOK7X
[PASS] Webhook URL найден: https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X

[INFO] Тестирование webhook: https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X
[INFO] Payload: {
  "video_url": "https://example.com/test/video/123",
  "tracker_id": "KT-TEST-123",
  "source_type": "user"
}

[INFO] Status Code: 200
[INFO] Response: { "success": true, "message": "Creative processed" }
[PASS] ✅ Webhook работает!

============================================================
[PASS] ✅ Webhook работает корректно!
```

## 💡 Использование в Cursor

Просто скажи:
```
"Проверь webhook для workflow dvZvUUmhtPzYOK7X"
```

Или:
```
"Проверь webhook https://kazamaqwe.app.n8n.cloud/webhook/dvZvUUmhtPzYOK7X"
```

