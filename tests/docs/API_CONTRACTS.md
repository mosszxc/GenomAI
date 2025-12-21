# GenomAI — API Contracts Documentation

**Версия:** v1.0  
**Статус:** ACTIVE  
**Назначение:** Детальная документация всех API контрактов для разработчиков

## 📋 Обзор

Этот документ описывает все API контракты системы GenomAI, включая:
- Webhook endpoints
- Request/Response форматы
- Правила валидации
- Обработку ошибок
- Примеры использования

> **Примечание:** Полная спецификация контрактов находится в [API_CONTRACTS.md](../../docs/layer-4-implementation-planning/API_CONTRACTS.md).  
> Этот документ — практическое руководство для разработчиков.

## 🔗 Webhook Endpoints

### 1. Creative Ingestion Webhook

**Endpoint:** `POST /ingest/creative`  
**Workflow:** `creative_ingestion_webhook`  
**STEP:** 01 — Ingestion

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Обязательные поля:**
- `video_url` (string, non-empty) — URL видео креатива
- `tracker_id` (string, non-empty) — ID трекера Keitaro
- `source_type` (string, enum: `"user"`) — тип источника (в STEP 01 только `"user"`)

**Правила валидации:**
- `video_url` должен быть валидным URL
- `tracker_id` должен быть непустой строкой
- `source_type` должен быть строго `"user"` (в STEP 01)
- Дополнительные поля игнорируются

#### Success Response

**Status Code:** `200 OK` или `201 Created`

**Body:**
```json
{
  "creative_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "registered",
  "message": "Creative registered successfully"
}
```

**Поведение:**
- Creative создан в `genomai.creatives`
- Событие `CreativeReferenceReceived` записано в `event_log`
- Событие `CreativeRegistered` записано в `event_log`

#### Idempotent Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "creative_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "registered",
  "message": "Creative already exists",
  "idempotent": true
}
```

**Поведение:**
- Дубль не создаётся
- Возвращается существующий `creative_id`
- Событие `CreativeRegistered` эмитируется (но creative не создаётся заново)

#### Error Responses

##### 400 Bad Request — Invalid Payload

**Причины:**
- Отсутствует обязательное поле
- Пустое значение обязательного поля
- Неверный `source_type`
- Невалидный JSON

**Response:**
```json
{
  "error": "Invalid payload",
  "message": "Missing required field: video_url",
  "event_type": "CreativeIngestionRejected"
}
```

**Поведение:**
- Creative не создаётся
- Событие `CreativeIngestionRejected` записывается в `event_log`
- Workflow останавливается

##### 500 Internal Server Error

**Причины:**
- Ошибка подключения к Supabase
- Ошибка записи в event_log
- Непредвиденная ошибка

**Response:**
```json
{
  "error": "Internal server error",
  "message": "Failed to create creative"
}
```

## 📊 Event Contracts

### CreativeReferenceReceived

**Когда эмитируется:** После успешной валидации payload, до записи в БД

**Payload:**
```json
{
  "event_type": "CreativeReferenceReceived",
  "entity_type": "creative",
  "entity_id": null,
  "payload": {
    "video_url": "https://example.com/video/12345",
    "tracker_id": "KT-123456",
    "source_type": "user"
  },
  "occurred_at": "2025-01-01T12:00:00Z",
  "idempotency_key": "creative_ref:video_url:tracker_id:hash"
}
```

### CreativeRegistered

**Когда эмитируется:** После успешного создания creative или при idempotent case

**Payload:**
```json
{
  "event_type": "CreativeRegistered",
  "entity_type": "creative",
  "entity_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "creative_id": "550e8400-e29b-41d4-a716-446655440000",
    "video_url": "https://example.com/video/12345",
    "tracker_id": "KT-123456",
    "source_type": "user"
  },
  "occurred_at": "2025-01-01T12:00:01Z",
  "idempotency_key": "creative_reg:550e8400-e29b-41d4-a716-446655440000"
}
```

### CreativeIngestionRejected

**Когда эмитируется:** При отклонении невалидного payload

**Payload:**
```json
{
  "event_type": "CreativeIngestionRejected",
  "entity_type": "creative",
  "entity_id": null,
  "payload": {
    "reason": "Missing required field: video_url",
    "received_payload": {
      "tracker_id": "KT-123456",
      "source_type": "user"
    }
  },
  "occurred_at": "2025-01-01T12:00:00Z",
  "idempotency_key": null
}
```

## 🔍 Примеры использования

### cURL

```bash
# Happy path
curl -X POST http://your-n8n-instance/webhook/ingest/creative \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video/12345",
    "tracker_id": "KT-123456",
    "source_type": "user"
  }'

# Idempotency check (тот же payload)
curl -X POST http://your-n8n-instance/webhook/ingest/creative \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video/12345",
    "tracker_id": "KT-123456",
    "source_type": "user"
  }'
```

### JavaScript (Node.js)

```javascript
const fetch = require('node-fetch');

async function ingestCreative(videoUrl, trackerId) {
  const response = await fetch('http://your-n8n-instance/webhook/ingest/creative', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      video_url: videoUrl,
      tracker_id: trackerId,
      source_type: 'user',
    }),
  });

  const data = await response.json();
  return data;
}

// Использование
ingestCreative('https://example.com/video/12345', 'KT-123456')
  .then(result => console.log('Creative ID:', result.creative_id))
  .catch(error => console.error('Error:', error));
```

### Python

```python
import requests

def ingest_creative(video_url, tracker_id):
    url = 'http://your-n8n-instance/webhook/ingest/creative'
    payload = {
        'video_url': video_url,
        'tracker_id': tracker_id,
        'source_type': 'user'
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# Использование
result = ingest_creative('https://example.com/video/12345', 'KT-123456')
print(f"Creative ID: {result['creative_id']}")
```

## ⚠️ Важные правила

1. **Idempotency:** Повторный запрос с теми же `video_url` и `tracker_id` не создаёт дубль
2. **Validation:** Все обязательные поля проверяются до записи в БД
3. **Events:** Все события записываются в `event_log` (append-only)
4. **Error Handling:** Ошибки валидации → HTTP 400, системные ошибки → HTTP 500
5. **Source Type:** В STEP 01 только `source_type = "user"` разрешён

## 📚 Связанные документы

- [API_CONTRACTS.md](../../docs/layer-4-implementation-planning/API_CONTRACTS.md) — Полная спецификация контрактов
- [01_ingestion_playbook.md](../../docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/01_ingestion_playbook.md) — Playbook для STEP 01
- [WEBHOOK_GUIDE.md](./WEBHOOK_GUIDE.md) — Руководство по работе с webhook'ами


