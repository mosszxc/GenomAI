# GenomAI — API & Contract Definitions (Layer 4)
Версия: v1.0
Статус: IMPLEMENTATION PLANNING / LAYER 4
Приоритет: Критический
Scope: MVP
Принцип: контракты описывают форму данных и обязательства, а не транспорт.

## 1. Purpose

Документ фиксирует контракты взаимодействия между компонентами системы:
- Telegram ↔ n8n
- n8n ↔ Supabase
- n8n ↔ Keitaro
- n8n ↔ LLM / Transcription (внешние)

**Цель:**
- исключить неявные договорённости,
- обеспечить идемпотентность,
- предотвратить смешение ответственности.

## 2. Contract Conventions (обязательные)

- Все идентификаторы — uuid (v4).
- Время — UTC, ISO 8601.
- Все payload'ы — JSON.
- Идемпотентность — через idempotency_key.
- Любой контракт допускает null для необязательных полей.
- Никакой логики в контрактах.

## 3. Telegram → Ingestion (Input Contract)

### 3.1 Submit Creative Reference

**Назначение:** приём ссылки на видео и tracker_id.

**Payload:**
```json
{
  "video_url": "https://...",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Обязательное:**
- video_url
- tracker_id

**Поведение:**
- создаётся CreativeReferenceReceived
- данные не валидируются на смысл

**Ошибки:**
- отсутствует поле → reject
- формат неверный → reject

## 4. n8n → Supabase (Write Contracts)

### 4.1 Create Creative

```json
{
  "creative_id": "uuid",
  "video_url": "https://...",
  "tracker_id": "KT-123456",
  "source_type": "user",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Правила:**
- creative_id генерируется один раз
- повтор = идемпотентен по video_url + tracker_id

### 4.2 Create Transcript (Immutable)

```json
{
  "transcript_id": "uuid",
  "creative_id": "uuid",
  "version": 1,
  "transcript_text": "...",
  "created_at": "2025-01-01T00:10:00Z"
}
```

**Правила:**
- новая версия = новая запись
- UPDATE запрещён

### 4.3 Create Decomposed Creative

```json
{
  "creative_id": "uuid",
  "schema_version": "v1",
  "payload": { "...": "..." },
  "created_at": "2025-01-01T00:12:00Z"
}
```

## 5. Event Contracts (EVENT_MODEL)

### 5.1 Emit Event (Generic)

```json
{
  "event_type": "DailyMetricsSnapshotCreated",
  "entity_type": "creative",
  "entity_id": "uuid",
  "payload": { "...": "..." },
  "occurred_at": "2025-01-02T00:00:00Z",
  "idempotency_key": "creative:date"
}
```

**Правила:**
- события append-only
- dedup по idempotency_key
- удаление/обновление запрещены

## 6. n8n ↔ Keitaro (Metrics Pull Contract)

### 6.1 Pull Raw Metrics

**Request (logical):**
```json
{
  "tracker_id": "KT-123456",
  "date": "2025-01-01"
}
```

**Response (normalized):**
```json
{
  "impressions": 1000,
  "clicks": 50,
  "conversions": 5,
  "spend": 25.0
}
```

**Правила:**
- данные считаются raw
- допускается отсутствие данных
- перезапись разрешена

## 7. Daily Snapshot Contract

### 7.1 Create Daily Metrics Snapshot

```json
{
  "creative_id": "uuid",
  "snapshot_date": "2025-01-01",
  "impressions_day": 1000,
  "clicks_day": 50,
  "conversions_day": 5,
  "spend_day": 25.0,
  "created_at": "2025-01-02T00:01:00Z"
}
```

**Правила:**
- один snapshot на день
- append-only
- отсутствие snapshot ≠ ошибка

## 8. Outcome Aggregation Contract

### 8.1 Create Outcome Aggregate

```json
{
  "creative_id": "uuid",
  "window_start": "2025-01-01",
  "window_end": "2025-01-03",
  "impressions": 3000,
  "conversions": 12,
  "spend": 75.0,
  "cpa": 6.25,
  "trend": "down",
  "volatility": 0.12,
  "environment_ctx": {
    "account_state": "stable",
    "platform_state": "normal"
  },
  "origin_type": "system",
  "created_at": "2025-01-04T00:00:00Z"
}
```

**Правила:**
- immutable
- используется только для learning

## 9. Learning Contract

### 9.1 Apply Outcome to Learning

```json
{
  "outcome_id": "uuid",
  "idea_id": "uuid",
  "applied_at": "2025-01-04T00:01:00Z"
}
```

**Правила:**
- допускается строго один раз
- только origin_type = system
- повтор → hard abort

## 10. Decision Engine Contract

### 10.1 Decision Output

```json
{
  "idea_id": "uuid",
  "decision": "approve | reject | defer",
  "decision_epoch": 3,
  "decision_trace_id": "uuid",
  "decided_at": "2025-01-01T00:20:00Z"
}
```

**Правила:**
- детерминированный
- воспроизводимый
- LLM не участвует

## 11. Hypothesis Factory Contract

### 11.1 Generate Hypothesis

```json
{
  "idea_id": "uuid",
  "hypothesis_id": "uuid",
  "transcript_text": "...",
  "version": 1,
  "generated_at": "2025-01-01T00:30:00Z"
}
```

## 12. Delivery Contract (Telegram)

```json
{
  "hypothesis_id": "uuid",
  "channel": "telegram",
  "delivered_at": "2025-01-01T00:31:00Z",
  "delivery_status": "sent"
}
```

## 13. Error Contracts (Summary)

- invalid payload → reject
- missing data → abort silently
- duplicate idempotency → ignore
- learning violation → hard abort

(Подробно см. ERROR_HANDLING.md)

## 14. Non-Contracts (явно)

**Не являются контрактами:**
- UI сообщения Telegram
- внутренние n8n переменные
- лог-сообщения
- LLM prompt тексты

## Final Rule

Если данные не соответствуют контракту —
они не существуют для системы.
