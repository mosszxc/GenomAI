# 07_outcome_ingestion_playbook.md

**STEP 07 — Outcome Ingestion (MVP)**

**Статус:** IMPLEMENTED
**Scope:** MVP
**Зависимости:**
- `06_telegram_output_playbook.md` (hypotheses доставлены)

**Следующий шаг:** `08_learning_loop_playbook.md`

## 0. Назначение шага

Этот шаг фиксирует реальность.

Outcome ingestion отвечает не на вопрос "почему",
а только на вопрос "что произошло".

На этом этапе:
- нет learning,
- нет интерпретаций,
- нет решений.

## 1. Входные данные

### 1.1 Источник

- Keitaro (tracking system)

### 1.2 Тип данных

- performance metrics (clicks, leads, spend, revenue, etc.)
- данные считаются:
  - шумными
  - неполными
  - запаздывающими

## 2. Реализация (Temporal)

**Workflow:** `KeitaroPollerWorkflow`
**Файл:** `temporal/workflows/keitaro_poller.py`
**Task Queue:** `metrics`
**Schedule:** Every 10 minutes

### 2.1 Trigger

- Schedule Trigger (cron)
- Frequency: каждые 10 минут

### 2.2 Load Keitaro Config

**Activity:** `load_keitaro_config`
**Таблица:** `keitaro_config`
**Фильтр:** `is_active = true`

### 2.3 Pull Raw Metrics

**Activity:** `fetch_keitaro_metrics`

**Логика:**
1. Get All Campaigns (`/admin_api/v1/campaigns`)
2. Extract Campaign IDs
3. For each campaign: Get Metrics (`/admin_api/v1/report/build`)
4. Aggregate metrics

**Параметры:**
- период: configurable window
- идентификация по `campaign_id` (= `tracker_id`)

### 2.4 Persist Raw Metrics

**Activity:** `save_raw_metrics`
**Таблица:** `raw_metrics_current`

**Поля:**
- tracker_id (text, primary key)
- date (date, not null)
- metrics (jsonb, not null)
- updated_at (timestamp, not null)

### 2.5 Emit Event

**RawMetricsObserved**

```json
{
  "tracker_id": "campaign_id_from_keitaro",
  "date": "YYYY-MM-DD"
}
```

## 3. Metrics Processing

**Workflow:** `MetricsProcessingWorkflow`
**Файл:** `temporal/workflows/metrics_processing.py`
**Schedule:** Every 30 minutes

### 3.1 Process Metrics to Outcomes

**Activity:** `process_metrics_to_outcomes`

Преобразует raw metrics в outcome_aggregates:
- Привязка к idea_id через creative → idea mapping
- Агрегация по windows (D1, D3, D7)

### 3.2 Create Daily Snapshot

**Activity:** `create_daily_snapshot`
**Таблица:** `daily_metrics_snapshot`

**Поля:**
- `id` (uuid)
- `tracker_id`
- `date`
- `metrics` (jsonb)
- `created_at`

### 3.3 Emit Event

**DailyMetricsSnapshotCreated**

```json
{
  "tracker_id": "campaign_id",
  "date": "YYYY-MM-DD",
  "snapshot_id": "uuid"
}
```

## 4. Хранилище

### 4.1 keitaro_config

```sql
keitaro_config (
  id          uuid primary key,
  domain      text not null,
  api_key     text not null,
  is_active   boolean not null default true,
  created_at  timestamp not null,
  updated_at  timestamp not null
)
```

### 4.2 raw_metrics_current (mutable)

```sql
raw_metrics_current (
  tracker_id  text primary key,
  date        date not null,
  metrics     jsonb not null,
  updated_at  timestamp not null
)
```

### 4.3 daily_metrics_snapshot (immutable)

```sql
daily_metrics_snapshot (
  id          uuid primary key,
  tracker_id  text not null,
  date        date not null,
  metrics     jsonb not null,
  created_at  timestamp not null,
  unique (tracker_id, date)
)
```

## 5. События

**Обязательные:**

### RawMetricsObserved

```json
{
  "tracker_id": "KT-123456",
  "date": "YYYY-MM-DD"
}
```

### DailyMetricsSnapshotCreated

```json
{
  "tracker_id": "KT-123456",
  "date": "YYYY-MM-DD",
  "snapshot_id": "uuid"
}
```

**Запрещённые:**

- любые learning events
- любые decision events

## 6. Definition of Done (DoD)

Шаг считается выполненным, если:
- Workflow запускается по расписанию
- raw metrics подтягиваются из Keitaro
- raw_metrics_current обновляется
- daily snapshot создаётся
- события эмитятся
- не происходит: интерпретация, learning, решения

## 7. Типовые ошибки (PR-блокеры)

❌ **обучение на raw данных**
❌ **принятие решений на raw данных**
❌ **realtime ingestion**
❌ **отсутствие snapshot layer**
❌ **"если данных мало — не сохраняем"**

## 8. Ручные проверки (обязательные)

### Check 1 — Happy path
- schedule отрабатывает
- snapshot появляется

### Check 2 — Missing data
- Keitaro вернул пусто
- workflow не падает

### Check 3 — Retry safety
- повторный запуск
- duplicate snapshot не создаётся

## 9. Выход шага

На выходе гарантировано:

**Система знает, что произошло,**
**но не знает, хорошо это или плохо.**

## 10. Жёсткие запреты

❌ learning
❌ интерпретация
❌ оптимизация
❌ decision

## 11. Готовность к следующему шагу

Можно переходить к `08_learning_loop_playbook.md`, если:
- snapshots создаются стабильно
- raw слой не ломает систему
- нет скрытой логики
