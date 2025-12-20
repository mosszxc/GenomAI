# 07_outcome_ingestion_playbook.md

**STEP 07 — Outcome Ingestion (MVP)**

**Статус:** IMPLEMENTATION PLAYBOOK  
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

## 2. n8n Workflow

**Workflow name:** `outcome_ingestion_keitaro`

### 2.1 Trigger

- **Node:** Scheduler (Cron)
- **Frequency:** 1 раз в сутки
- **Time:** фиксированное (например, 03:00 UTC)

📌 **Нет realtime ingestion в MVP.**

### 2.2 Pull Raw Metrics

- **Node:** HTTP Request (Keitaro API)

**Параметры:**
- период: last 24h
- идентификация по tracker_id

📌 **Ошибка Keitaro ≠ ошибка системы.**

### 2.3 Persist Raw Metrics (Mutable)

- **Node:** Supabase Upsert
- **Таблица:** `raw_metrics_current`

**Поля (примерно):**
- tracker_id
- date
- impressions
- clicks
- leads
- revenue
- spend
- updated_at

📌 **UPDATE разрешён.**

### 2.4 Emit Event

**RawMetricsObserved**

```json
{
  "tracker_id": "KT-123456",
  "date": "YYYY-MM-DD"
}
```

### 2.5 Daily Snapshot Creation

- **Node:** Supabase Insert
- **Таблица:** `daily_metrics_snapshot`

**Поля:**
- `id` (uuid)
- `tracker_id`
- `date`
- `metrics` (jsonb)
- `created_at`

📌 **append-only**  
📌 **отсутствие snapshot = валидно**

### 2.6 Emit Event

**DailyMetricsSnapshotCreated**

```json
{
  "tracker_id": "KT-123456",
  "date": "YYYY-MM-DD",
  "snapshot_id": "uuid"
}
```

## 3. Хранилище

### 3.1 raw_metrics_current (mutable)

```sql
raw_metrics_current (
  tracker_id  text primary key,
  date        date not null,
  metrics     jsonb not null,
  updated_at  timestamp not null
)
```

### 3.2 daily_metrics_snapshot (immutable)

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

## 4. События

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

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ raw metrics подтягиваются по cron
- ✅ raw_metrics_current обновляется
- ✅ daily snapshot создаётся
- ✅ события эмитятся
- ✅ не происходит:
  - интерпретация
  - learning
  - принятие решений

## 6. Типовые ошибки (PR-блокеры)

❌ **обучение на raw данных**  
❌ **принятие решений на raw данных**  
❌ **realtime ingestion**  
❌ **отсутствие snapshot layer**  
❌ **"если данных мало — не сохраняем"**

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- cron отрабатывает
- snapshot появляется

### Check 2 — Missing data
- Keitaro вернул пусто
- workflow не падает

### Check 3 — Retry safety
- повторный cron
- duplicate snapshot не создаётся

## 8. Выход шага

На выходе гарантировано:

**Система знает, что произошло,**
**но не знает, хорошо это или плохо.**

## 9. Жёсткие запреты

❌ learning  
❌ интерпретация  
❌ оптимизация  
❌ decision

## 10. Готовность к следующему шагу

Можно переходить к `08_learning_loop_playbook.md`, если:
- ✅ snapshots создаются стабильно
- ✅ raw слой не ломает систему
- ✅ нет скрытой логики
