# GenomAI — Physical Data Schemas (Supabase / PostgreSQL)
Версия: v1.0
Статус: IMPLEMENTATION PLANNING / LAYER 4
Приоритет: Критический
Scope: MVP
DB: Supabase PostgreSQL

## 1. Purpose

Документ определяет физические структуры хранения данных:
- таблицы
- поля
- ключи
- ограничения
- правила mutability

Документ не содержит бизнес-логики и не описывает запросы.
Он фиксирует форму данных, а не поведение.

## 2. Global Schema Rules (обязательные)

- **Append-only по умолчанию**
  - Если не указано явно — записи не обновляются.
- **Immutable facts**
  - Events, snapshots, outcomes — не перезаписываются.
- **Versioned state**
  - Любое "состояние" хранится как версии.
- **Soft relations**
  - FK логические (через *_id), без каскадных delete.

## 3. Core Identity Tables

### 3.1 creatives

Источник истины для креативов.

```sql
creatives (
  id                uuid PK,
  video_url         text not null,
  tracker_id        text not null,
  created_at        timestamp not null,
  source_type       text check (source_type in ('system','user')),
  status            text
)
```

### 3.2 ideas

Абстрактная идея (каноническая сущность).

```sql
ideas (
  id                uuid PK,
  canonical_hash    text unique not null,
  cluster_id        uuid,
  created_at        timestamp not null,
  status            text
)
```

## 4. Transcription & Decomposition

### 4.1 transcripts

Immutable версии транскриптов.

```sql
transcripts (
  id                uuid PK,
  creative_id       uuid not null,
  version           int not null,
  transcript_text   text not null,
  created_at        timestamp not null,
  UNIQUE (creative_id, version)
)
```

### 4.2 decomposed_creatives

Результат Canonical Schema.

```sql
decomposed_creatives (
  id                uuid PK,
  creative_id       uuid not null,
  schema_version    text not null,
  payload           jsonb not null,
  created_at        timestamp not null
)
```

## 5. Event Log (EVENT_MODEL)

### 5.1 event_log (append-only)

```sql
event_log (
  id                uuid PK,
  event_type        text not null,
  entity_type       text,
  entity_id         uuid,
  payload           jsonb,
  occurred_at       timestamp not null,
  idempotency_key   text
)
```

**Правила:**
- idempotency_key используется для dedup
- записи не обновляются и не удаляются

## 6. Metrics Storage

### 6.1 Raw Metrics (mutable)

```sql
raw_metrics_current (
  creative_id       uuid PK,
  impressions       int,
  clicks            int,
  conversions       int,
  spend             numeric,
  updated_at        timestamp
)
```

⚠️ **НЕ используется для learning**

### 6.2 Daily Snapshots (append-only)

```sql
daily_metrics_snapshot (
  id                uuid PK,
  creative_id       uuid not null,
  snapshot_date     date not null,
  impressions_day   int,
  clicks_day        int,
  conversions_day   int,
  spend_day         numeric,
  created_at        timestamp not null,
  UNIQUE (creative_id, snapshot_date)
)
```

## 7. Outcome Aggregation

### 7.1 outcome_aggregates (immutable)

```sql
outcome_aggregates (
  id                uuid PK,
  creative_id       uuid not null,
  window_id         text,
  window_start      date not null,
  window_end        date not null,
  impressions       int,
  conversions       int,
  spend             numeric,
  cpa               numeric,
  trend             text,
  volatility        numeric,
  environment_ctx   jsonb,
  origin_type       text not null check (origin_type in ('system','user')),
  decision_id       uuid,
  created_at        timestamp not null,
  UNIQUE (creative_id, window_start, window_end),
  CHECK (
    (origin_type = 'system' AND decision_id IS NOT NULL)
    OR
    (origin_type = 'user')
  )
)
```

**Примечание о window_id:**
- `window_id` — опциональное поле для удобства эксплуатации (например, "D1_D3", "D1_D7", "D1_D14")
- На MVP не обязателен (nullable), но рекомендован для:
  - упрощения построения idempotency keys в event_log
  - упрощения фильтрации окон по типам
  - более читаемых запросов и логов
- Заполняется при создании записи (в n8n) или через computed logic вне БД
- Уникальность окна по-прежнему обеспечивается через `(creative_id, window_start, window_end)`

**❗ Критическое правило зависимости:**
- `origin_type = system` → требует `decision_id` (NOT NULL)
- `origin_type = user` → `decision_id` nullable (может быть NULL)

**Правила:**
- `decision_id` immutable (не изменяется после создания)
- FK логический (через `decision_id`), без каскадных delete
- CHECK constraint гарантирует causal chain: system outcome всегда связан с Decision

**❗ ПОДТВЕРЖДЕНИЕ СТРУКТУРЫ (GLOBAL ARCHITECTURAL PATCH):**

**Схема уже поддерживает:**
- ✅ `origin_type` (system | user) — NOT NULL, CHECK constraint
- ✅ `decision_id` — nullable, обязателен для `origin_type = system` через CHECK constraint
- ✅ `cpa` (CPA_window) — единственная метрика успешности в MVP
- ✅ `trend`, `volatility` — derived от CPA_window

**Семантика:**
- `origin_type = system` → требует `decision_id IS NOT NULL` (enforced через CHECK)
- `origin_type = user` → `decision_id` nullable (может быть NULL)
- `cpa` (CPA_window) — единственная метрика для learning/decision в MVP
- CTR, CVR, ROAS не хранятся как метрики успешности (только observability, если нужно)

**Никаких новых полей не вводить.**

### 7.2 Migration SQL (для существующих таблиц)

Если таблица `outcome_aggregates` уже создана без `decision_id`, выполните следующую миграцию:

```sql
-- 1. Add decision_id column
ALTER TABLE outcome_aggregates
ADD COLUMN decision_id uuid;

-- 2. Enforce constraint: system outcomes must have decision_id
ALTER TABLE outcome_aggregates
ADD CONSTRAINT outcome_aggregates_decision_id_required_for_system
CHECK (
  (origin_type = 'system' AND decision_id IS NOT NULL)
  OR
  (origin_type = 'user')
);

-- 3. (Recommended) Index for joins / lookups
CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_decision_id
ON outcome_aggregates(decision_id)
WHERE origin_type = 'system';

-- 4. (Optional but clean) Ensure origin_type is not null
ALTER TABLE outcome_aggregates
ALTER COLUMN origin_type SET NOT NULL;
```

**Примечания:**
- FK можно оставить "soft" (логический), без FOREIGN KEY constraint'ов и каскадов
- Индекс создаётся только для `origin_type = 'system'` (частичный индекс) для оптимизации
- Если в таблице уже есть записи с `origin_type = 'system'` без `decision_id`, миграция не пройдёт — сначала нужно исправить данные

### 7.3 Migration SQL (опционально — для window_id)

Если требуется добавить `window_id` для удобства эксплуатации:

```sql
-- 1. Add window_id column (optional, nullable on MVP)
ALTER TABLE outcome_aggregates
ADD COLUMN window_id text;

-- 2. (Recommended) Index for filtering by window type
CREATE INDEX IF NOT EXISTS idx_outcome_aggregates_window_id
ON outcome_aggregates(window_id);
```

**Примечания:**
- `window_id` опционален на MVP (nullable)
- Заполняется при создании записи в n8n или через computed logic
- Индекс полезен для фильтрации окон по типам (например, все D1_D3 outcomes)
- В будущем можно сделать NOT NULL и добавить в UNIQUE constraint, если потребуется

## 8. Learning Memory (Versioned State)

### 8.1 idea_confidence_versions

```sql
idea_confidence_versions (
  id                uuid PK,
  idea_id           uuid not null,
  confidence_value  numeric not null,
  version           int not null,
  updated_at        timestamp not null,
  source_outcome_id uuid not null,
  UNIQUE (idea_id, version),
  CHECK (source_outcome_id IS NOT NULL)
)
```

**❗ Критическое правило:**
- `source_outcome_id` обязателен (NOT NULL)
- Manual learning updates запрещены — все обновления confidence должны быть связаны с Outcome
- Learning происходит только через Learning Loop Service на основе Outcome

### 8.2 fatigue_state_versions

```sql
fatigue_state_versions (
  id                uuid PK,
  idea_id           uuid not null,
  fatigue_value     numeric not null,
  version           int not null,
  updated_at        timestamp not null,
  source_outcome_id uuid not null,
  UNIQUE (idea_id, version),
  CHECK (source_outcome_id IS NOT NULL)
)
```

**❗ Критическое правило:**
- `source_outcome_id` обязателен (NOT NULL)
- Manual learning updates запрещены — все обновления fatigue должны быть связаны с Outcome
- Learning происходит только через Learning Loop Service на основе Outcome

### 8.3 Migration SQL (для существующих таблиц)

Если таблицы `idea_confidence_versions` или `fatigue_state_versions` уже созданы с nullable `source_outcome_id`, выполните следующую миграцию:

```sql
-- 1) Make source_outcome_id mandatory
ALTER TABLE idea_confidence_versions
ALTER COLUMN source_outcome_id SET NOT NULL;

ALTER TABLE fatigue_state_versions
ALTER COLUMN source_outcome_id SET NOT NULL;

-- 2) (Recommended) Index to trace learning provenance
CREATE INDEX IF NOT EXISTS idx_idea_confidence_versions_source_outcome
ON idea_confidence_versions(source_outcome_id);

CREATE INDEX IF NOT EXISTS idx_fatigue_state_versions_source_outcome
ON fatigue_state_versions(source_outcome_id);
```

**Примечания:**
- Если в таблицах уже есть записи с `source_outcome_id IS NULL`, миграция не пройдёт — сначала нужно удалить такие записи или связать их с существующими Outcome
- Индексы создаются для быстрого поиска learning records по source Outcome (provenance tracking)
- Это обеспечивает enforce правила: learning только от aggregated system outcome

## 9. Hypotheses & Delivery

### 9.1 hypotheses

```sql
hypotheses (
  id                uuid PK,
  idea_id           uuid not null,
  transcript_text   text not null,
  version           int not null,
  created_at        timestamp not null,
  status            text
)
```

### 9.2 deliveries

```sql
deliveries (
  id                uuid PK,
  hypothesis_id     uuid not null,
  channel           text,
  delivered_at      timestamp not null,
  delivery_status   text
)
```

## 10. Forbidden Operations (жёстко)

**Запрещено:**
- UPDATE event_log
- UPDATE daily_metrics_snapshot
- UPDATE outcome_aggregates (включая изменение decision_id)
- UPDATE learning tables без новой версии
- learning без origin_type = system
- создание outcome_aggregates с origin_type = system без decision_id (CHECK constraint предотвращает)
- **manual learning updates** — создание записей в `idea_confidence_versions` или `fatigue_state_versions` без `source_outcome_id` (CHECK constraint предотвращает)
- создание learning records с `source_outcome_id IS NULL` (CHECK constraint предотвращает)

## 11. Indexing Guidance (non-exhaustive)

Рекомендуемые индексы:
- event_log (event_type, occurred_at)
- daily_metrics_snapshot (creative_id, snapshot_date)
- outcome_aggregates (creative_id, window_start, window_end)
- outcome_aggregates (decision_id) WHERE origin_type = 'system' (частичный индекс для быстрого поиска system outcomes по Decision)
- outcome_aggregates (window_id) (опционально, для фильтрации окон по типам)
- idea_confidence_versions (idea_id, version desc)
- idea_confidence_versions (source_outcome_id) (для provenance tracking — поиск learning records по source Outcome)
- fatigue_state_versions (source_outcome_id) (для provenance tracking — поиск learning records по source Outcome)

## 12. Final Rule

Если данные можно перезаписать —
они не могут быть источником истины для обучения.
