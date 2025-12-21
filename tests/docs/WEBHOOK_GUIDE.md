# GenomAI — Webhook Guide

**Версия:** v1.0  
**Статус:** ACTIVE  
**Назначение:** Практическое руководство по работе с webhook'ами GenomAI

## 📋 Обзор

Этот документ описывает, как работать с webhook'ами GenomAI в n8n:
- Настройка webhook trigger
- Получение webhook URL
- Тестирование webhook'ов
- Troubleshooting

## 🔧 Настройка Webhook в n8n

### 1. Создание Webhook Trigger

1. Откройте n8n workflow editor
2. Добавьте новый node: **Webhook**
3. Настройте параметры:
   - **HTTP Method:** `POST`
   - **Path:** `/ingest/creative`
   - **Response Mode:** `Last Node` (или `When Last Node Finishes`)
   - **Options → On Error:** `Continue Regular Output`

### 2. Получение Webhook URL

После сохранения workflow, n8n предоставит webhook URL:

```
https://your-n8n-instance.com/webhook/ingest/creative
```

или для локальной разработки:

```
http://localhost:5678/webhook/ingest/creative
```

**Важно:** URL доступен только если workflow активен (enabled).

### 3. Тестирование Webhook

#### Использование cURL

```bash
curl -X POST http://localhost:5678/webhook/ingest/creative \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video/12345",
    "tracker_id": "KT-123456",
    "source_type": "user"
  }'
```

#### Использование тестовых скриптов

```bash
# Bash скрипт
export WEBHOOK_URL="http://localhost:5678/webhook/ingest/creative"
./tests/scripts/test_ingestion.sh

# Node.js скрипт
export WEBHOOK_URL="http://localhost:5678/webhook/ingest/creative"
node tests/scripts/test_ingestion.js
```

## 🧪 Тестовые сценарии

### Happy Path

```bash
curl -X POST $WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d @tests/payloads/ingestion/happy_path.json
```

**Ожидается:**
- HTTP 200/201
- Creative создан в БД
- 2 события в event_log

### Idempotency

```bash
# Первый запрос
curl -X POST $WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d @tests/payloads/ingestion/happy_path.json

# Повторный запрос (тот же payload)
curl -X POST $WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d @tests/payloads/ingestion/idempotency.json
```

**Ожидается:**
- Оба запроса возвращают HTTP 200
- Второй запрос не создаёт дубль
- Возвращается тот же `creative_id`

### Invalid Payload

```bash
curl -X POST $WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d @tests/payloads/ingestion/invalid_missing_video_url.json
```

**Ожидается:**
- HTTP 400
- Creative не создан
- Событие `CreativeIngestionRejected` в event_log

## 🔍 Troubleshooting

### Проблема: Webhook не отвечает

**Возможные причины:**
1. Workflow не активен (не enabled)
2. Неверный URL
3. n8n instance не запущен

**Решение:**
- Проверьте, что workflow enabled в n8n
- Убедитесь, что n8n instance запущен
- Проверьте URL в n8n workflow settings

### Проблема: HTTP 500 Internal Server Error

**Возможные причины:**
1. Ошибка подключения к Supabase
2. Ошибка записи в event_log
3. Ошибка в workflow логике

**Решение:**
- Проверьте Supabase credentials в n8n
- Проверьте логи n8n execution
- Убедитесь, что схема `genomai` экспонирована в Supabase

### Проблема: HTTP 400, но payload валидный

**Возможные причины:**
1. Неверный Content-Type header
2. Невалидный JSON
3. Отсутствуют обязательные поля

**Решение:**
- Убедитесь, что `Content-Type: application/json`
- Проверьте JSON синтаксис
- Проверьте наличие всех обязательных полей

### Проблема: Дубль создаётся при повторном запросе

**Возможные причины:**
1. Idempotency check не работает
2. UNIQUE constraint не настроен в БД

**Решение:**
- Проверьте, что в workflow есть idempotency check
- Убедитесь, что в таблице `creatives` есть UNIQUE constraint на `(video_url, tracker_id)`

## 📝 Best Practices

1. **Всегда используйте Content-Type header:**
   ```bash
   -H "Content-Type: application/json"
   ```

2. **Проверяйте event_log после каждого запроса:**
   ```sql
   SELECT * FROM genomai.event_log 
   ORDER BY occurred_at DESC 
   LIMIT 10;
   ```

3. **Используйте тестовые скрипты для автоматизации:**
   ```bash
   ./tests/scripts/test_ingestion.sh
   ```

4. **Логируйте все запросы для отладки:**
   - Используйте n8n execution history
   - Проверяйте event_log в Supabase

## 🔗 Связанные документы

- [API_CONTRACTS.md](./API_CONTRACTS.md) — Детальная документация API
- [test_ingestion.sh](../scripts/test_ingestion.sh) — Тестовый скрипт
- [01_ingestion_playbook.md](../../docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/01_ingestion_playbook.md) — Playbook для STEP 01


