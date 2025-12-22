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

**Workflow name:** `Outcome Ingestion Keitaro`  
**Workflow ID:** `zMHVFT2rM7PpTiJj`  
**Статус:** Создан, требует тестирования

### 2.1 Trigger

- **Node:** Schedule Trigger (Cron)
- **Frequency:** 1 раз в сутки
- **Time:** 03:00 UTC (cron: `0 3 * * *`)
- **Manual Trigger:** Для тестирования и отладки

📌 **Нет realtime ingestion в MVP.**

### 2.2 Load Keitaro Config

- **Node:** Supabase Get
- **Таблица:** `keitaro_config`
- **Фильтр:** `is_active = true`

**Назначение:** Загрузка активной конфигурации Keitaro (domain и api_key) из БД.

📌 **Credentials хранятся в БД, а не в environment variables.**

### 2.3 Pull Raw Metrics

**Логика:**
1. **Get All Campaigns** (HTTP Request GET `/admin_api/v1/campaigns`)
   - Получить список всех кампаний из Keitaro
   - Headers: `Api-Key: {{ api_key }}`
2. **Extract Campaign IDs** (Function node)
   - Извлечь `campaign_id` из каждой кампании
   - `campaign_id` = `tracker_id` в нашей системе
3. **Loop Over Campaigns** (SplitInBatches)
   - Итерация по всем `campaign_id`
4. **Get Campaign Metrics** (HTTP Request POST `/admin_api/v1/report/build`)
   - Для каждой кампании получить метрики за вчерашний день
   - Фильтр: `campaign_id` = текущий `tracker_id`
   - Период: last 24h (yesterday)
5. **Check Has Data** (IF node)
   - Проверка наличия данных (rows.length > 0)
   - Если данных нет → возврат в цикл (пропуск кампании)
   - Если данные есть → обработка

**Параметры:**
- период: last 24h (yesterday)
- идентификация по `campaign_id` (который = `tracker_id`)

📌 **Ошибка Keitaro ≠ ошибка системы.**  
📌 **Если данных нет для кампании → пропускаем, не падаем.**

### 2.4 Aggregate Metrics

- **Node:** Function node
- **Назначение:** Агрегация метрик из Keitaro response
- **Поля:**
  - `clicks` (сумма всех clicks)
  - `conversions` (сумма всех conversions/leads)
  - `revenue` (сумма всего revenue)
  - `cost` (сумма всего cost/spend)

### 2.5 Persist Raw Metrics (Mutable)

- **Node:** Supabase Get → IF → Update/Create
- **Таблица:** `raw_metrics_current`

**Логика:**
1. **Persist Raw Metrics** (Supabase Get)
   - Проверка существования записи по `tracker_id` и `date`
2. **Check Exists** (IF node)
   - Если существует → Update
   - Если не существует → Create
3. **Update Raw Metrics** / **Create Raw Metrics**
   - Сохранение агрегированных метрик

**Поля:**
- tracker_id (text, primary key)
- date (date, not null)
- metrics (jsonb, not null) - содержит: clicks, conversions, revenue, cost
- updated_at (timestamp, not null)

📌 **UPDATE разрешён.**

### 2.6 Emit Event

**RawMetricsObserved**

- **Node:** Supabase Create (event_log)
- **Event Type:** `RawMetricsObserved`
- **Entity Type:** `tracker`
- **Entity ID:** `tracker_id`
- **Payload:**
```json
{
  "tracker_id": "campaign_id_from_keitaro",
  "date": "YYYY-MM-DD"
}
```

### 2.7 Daily Snapshot Creation

- **Node:** Supabase Create
- **Таблица:** `daily_metrics_snapshot`

**Поля:**
- `id` (uuid, primary key, auto-generated)
- `tracker_id` (text, not null)
- `date` (date, not null)
- `metrics` (jsonb, not null) - содержит: clicks, conversions, revenue, cost
- `created_at` (timestamp, not null, default now())

**Unique constraint:** `(tracker_id, date)` - предотвращает дубликаты

📌 **append-only**  
📌 **отсутствие snapshot = валидно**

### 2.8 Emit Event

**DailyMetricsSnapshotCreated**

- **Node:** Supabase Create (event_log)
- **Event Type:** `DailyMetricsSnapshotCreated`
- **Entity Type:** `tracker`
- **Entity ID:** `tracker_id`
- **Payload:**
```json
{
  "tracker_id": "campaign_id_from_keitaro",
  "date": "YYYY-MM-DD",
  "snapshot_id": "uuid"
}
```

## 3. Хранилище

### 3.1 keitaro_config (configuration)

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

📌 **Только одна активная конфигурация должна существовать.**

### 3.2 raw_metrics_current (mutable)

```sql
raw_metrics_current (
  tracker_id  text primary key,
  date        date not null,
  metrics     jsonb not null,
  updated_at  timestamp not null
)
```

### 3.3 daily_metrics_snapshot (immutable)

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
- ✅ Workflow создан и настроен
- ✅ raw metrics подтягиваются по cron
- ✅ raw_metrics_current обновляется
- ✅ daily snapshot создаётся
- ✅ события эмитятся
- ✅ не происходит:
  - интерпретация
  - learning
  - принятие решений

**Текущий статус:**
- ✅ Workflow создан (ID: `zMHVFT2rM7PpTiJj`)
- ⏳ Требуется тестирование
- ⏳ Требуется проверка данных в БД

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

