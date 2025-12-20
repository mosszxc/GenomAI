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
  window_start      date not null,
  window_end        date not null,
  impressions       int,
  conversions       int,
  spend             numeric,
  cpa               numeric,
  trend             text,
  volatility        numeric,
  environment_ctx   jsonb,
  origin_type       text check (origin_type in ('system','user')),
  created_at        timestamp not null,
  UNIQUE (creative_id, window_start, window_end)
)
```

## 8. Learning Memory (Versioned State)

### 8.1 idea_confidence_versions

```sql
idea_confidence_versions (
  id                uuid PK,
  idea_id           uuid not null,
  confidence_value  numeric not null,
  version           int not null,
  updated_at        timestamp not null,
  source_outcome_id uuid,
  UNIQUE (idea_id, version)
)
```

### 8.2 fatigue_state_versions

```sql
fatigue_state_versions (
  id                uuid PK,
  idea_id           uuid not null,
  fatigue_value     numeric not null,
  version           int not null,
  updated_at        timestamp not null,
  source_outcome_id uuid,
  UNIQUE (idea_id, version)
)
```

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
- UPDATE outcome_aggregates
- UPDATE learning tables без новой версии
- learning без origin_type = system

## 11. Indexing Guidance (non-exhaustive)

Рекомендуемые индексы:
- event_log (event_type, occurred_at)
- daily_metrics_snapshot (creative_id, snapshot_date)
- outcome_aggregates (creative_id, window_start, window_end)
- idea_confidence_versions (idea_id, version desc)

## 12. Final Rule

Если данные можно перезаписать —
они не могут быть источником истины для обучения.
