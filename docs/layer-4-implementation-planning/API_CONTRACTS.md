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
  "window_id": "D1_D3",
  "window_definition": {
    "start": "2025-01-01",
    "end": "2025-01-03",
    "type": "D1-D3"
  },
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
  "idempotency_key": "creative:uuid:window:D1_D3",
  "created_at": "2025-01-04T00:00:00Z"
}
```

**Обязательные поля:**
- creative_id
- window_id (предпочтительно) или window_definition
- window_start, window_end (для обратной совместимости)
- origin_type
- idempotency_key

**❗ КРИТИЧЕСКОЕ ПРАВИЛО ДЛЯ РЕАЛИЗАЦИИ:**

**Idempotency Key Rule:**

**idempotency_key = creative_id + window_definition**

**Детали:**
- window_id — строковый идентификатор окна (например, "D1_D3", "D1_D7", "D1_D14")
- window_definition — объект с полями:
  - start: дата начала окна (ISO 8601)
  - end: дата конца окна (ISO 8601)
  - type: тип окна (например, "D1-D3", "D1-D7", "D1-D14")
- window_id и window_definition должны быть согласованы (window_id должен соответствовать window_definition)
- idempotency_key формируется как: `creative_id:window_id` или `creative_id:window_definition.type`

**⚠️ Имплементационная ловушка:**
В n8n разработчик **НЕ должен**:
- ❌ создавать Outcome Aggregate без window_id или window_definition
- ❌ использовать только window_start/window_end без window_id
- ❌ генерировать idempotency_key без учёта window_definition
- ❌ допускать несоответствие между window_id и window_definition

**Правильный подход:**
- ✅ Всегда включать window_id (предпочтительно) или window_definition в контракт
- ✅ Формировать idempotency_key как: `creative_id:window_id`
- ✅ Гарантировать, что window_id соответствует window_definition
- ✅ Использовать window_id для быстрого поиска и дедупликации

**Правила:**
- immutable
- используется только для learning
- idempotency_key обязателен для предотвращения дубликатов
- window_id обязателен (или window_definition) — окно является сущностью в Event Model и Storage Model

**❗ ПОДТВЕРЖДЕНИЕ СТРУКТУРЫ (GLOBAL ARCHITECTURAL PATCH):**

**Структура контракта уже поддерживает:**
- ✅ `origin_type` (system | user) — обязательное поле
- ✅ `decision_id` — nullable, обязателен для `origin_type = system`
- ✅ `cpa` (CPA_window) — единственная метрика успешности в MVP

**Семантика:**
- `origin_type = system` → требует `decision_id IS NOT NULL` и `hypothesis_id IS NOT NULL`
- `origin_type = user` → `decision_id` nullable и `hypothesis_id` nullable
- `cpa` (CPA_window) — единственная метрика для learning/decision в MVP
- CTR, CVR, ROAS не используются для learning/decision (только observability)

**Никаких новых полей не вводить.**

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
- требует decision_id IS NOT NULL и hypothesis_id IS NOT NULL
- повтор → hard abort

**❗ ПОДТВЕРЖДЕНИЕ (GLOBAL ARCHITECTURAL PATCH):**

**OutcomeAppliedToLearning разрешён только для `origin_type = system`.**

**User Outcome (`origin_type = user`) никогда не триггерит OutcomeAppliedToLearning.**

## 10. Decision Engine Contract (Render API)

**⚠️ ВАЖНО:** Decision Engine мигрирован на Render. n8n вызывает Render API.

### 10.1 n8n → Render API (Request)

**Endpoint:** `POST /api/decision`

**Request:**
```json
{
  "idea_id": "uuid",
  "idea": {
    "id": "uuid",
    "canonical_hash": "string",
    "active_cluster_id": "uuid",
    "angle_type": "enum",
    "core_belief": "enum",
    "promise_type": "enum",
    "state_before": "enum",
    "state_after": "enum",
    "context_frame": "enum",
    "status": "string",
    "risk_level": "enum",
    "horizon": "enum"
  },
  "system_state": {
    "current_state": "enum",
    "risk_budget": 1000,
    "max_active_ideas": 100,
    "active_ideas_count": 50
  },
  "fatigue_state": {
    "idea_id": "uuid",
    "fatigue_level": "enum"
  },
  "death_memory": {
    "idea_id": "uuid",
    "is_dead": false
  }
}
```

**Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer {API_KEY}`

### 10.2 Render API → n8n (Response)

**Success Response:**
```json
{
  "success": true,
  "decision": {
    "decision_id": "uuid",
    "idea_id": "uuid",
    "decision_type": "APPROVE" | "REJECT" | "DEFER" | "ALLOW_WITH_CONSTRAINTS",
    "decision_reason": "string",
    "passed_checks": ["check1", "check2"],
    "failed_checks": [],
    "failed_check": null,
    "dominant_constraint": null,
    "cluster_at_decision": "uuid",
    "horizon": "enum",
    "system_state": "enum",
    "policy_version": "v1.0",
    "timestamp": "2025-01-01T00:20:00Z"
  },
  "decision_trace": {
    "id": "uuid",
    "decision_id": "uuid",
    "checks": [
      {
        "check_name": "schema_validity",
        "order": 1,
        "result": "PASSED",
        "details": {}
      }
    ],
    "result": "APPROVE",
    "created_at": "2025-01-01T00:20:00Z"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "IDEA_NOT_FOUND" | "INVALID_INPUT" | "SUPABASE_ERROR" | "INTERNAL_ERROR",
    "message": "string",
    "details": {}
  }
}
```

**Правила:**
- Decision Engine детерминированный
- Decision Engine воспроизводимый
- LLM не участвует
- Decision и Decision Trace сохраняются в Supabase Render API
- n8n получает результат и эмитит событие DecisionMade

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
