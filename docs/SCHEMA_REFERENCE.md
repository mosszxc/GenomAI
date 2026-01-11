# Schema Reference

Единый источник истины для схемы БД GenomAI.

**Last updated:** 2026-01-11

---

## Naming Convention

| Concept | Workflow Name | Table Name | API Endpoint |
|---------|---------------|------------|--------------|
| Idea | `idea_registry_create` | `ideas` | - |
| Decision | `decision_engine_mvp` | `decisions` | `/api/decision/` |
| Decision Trace | - | `decision_traces` | - |
| Decomposed Creative | `creative_decomposition_llm` | `decomposed_creatives` | - |
| Transcript | `creative_transcription` | `transcripts` | - |
| Hypothesis | `hypothesis_factory_generate` | `hypotheses` | - |
| Confidence | - | `idea_confidence_versions` | - |
| Fatigue | - | `fatigue_state_versions` | - |
| Outcome | `outcome_aggregator` | `outcome_aggregates` | - |
| Learning | `learning_loop_v2` | `outcome_aggregates.learning_applied` | `/learning/process` |

---

## Common Naming Mistakes

| Wrong (legacy/issue) | Correct |
|---------------------|---------|
| `idea_registry` (table) | `ideas` |
| `decision_log` | `decisions` |
| `atoms` | `decomposed_creatives` |
| `atom_weights` | `idea_confidence_versions` |
| `learning_events` | Нет таблицы, флаг `learning_applied` |

---

## Tables Overview

### Core Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `creatives` | Входящие креативы | Yes (status) | buyer_creative, transcription |
| `transcripts` | Транскрипты видео | No (append-only) | transcription |
| `decomposed_creatives` | LLM-разбор | No (append-only) | decomposition |
| `ideas` | Канонические идеи | Yes (death_state) | idea_registry, learning |
| `decisions` | Решения DE | No (append-only) | Decision Engine API |

#### decisions (constraints)
```
PK: id
UNIQUE: (idea_id, decision_epoch)  -- Idempotency guard (#284)
CHECK: decision IN ('approve', 'reject', 'defer')
```
| `decision_traces` | Trace решений | No (append-only) | Decision Engine API |
| `hypotheses` | Генерированные гипотезы | Yes (status) | hypothesis_factory |
| `deliveries` | Лог доставок | No (append-only) | telegram_delivery |

#### hypotheses (retry columns, Issue #313)
```
retry_count     INT DEFAULT 0      -- Delivery retry attempts (max 3)
last_retry_at   TIMESTAMPTZ        -- Last retry timestamp
last_error      TEXT               -- Last delivery error message
```
Status flow: `null` -> `failed` -> (retry) -> `delivered` | `abandoned`

### Metrics Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `raw_metrics_current` | Текущие метрики | Yes (upsert) | keitaro_poller |
| `daily_metrics_snapshot` | Daily snapshots | No (append-only) | snapshot_creator |
| `outcome_aggregates` | Агрегированные outcomes | Yes (learning_applied) | outcome_aggregator |

#### raw_metrics_current (актуальная схема)
```
tracker_id  TEXT      PK   -- Keitaro tracker ID
date        DATE           -- Date of metrics
metrics     JSONB          -- Raw metrics (impressions, clicks, leads, revenue, spend)
updated_at  TIMESTAMP      -- Last update time
```

#### daily_metrics_snapshot (актуальная схема)
```
id          UUID      PK   -- Auto-generated
tracker_id  TEXT           -- Keitaro tracker ID
date        DATE           -- Snapshot date
metrics     JSONB          -- Metrics snapshot
created_at  TIMESTAMP      -- When snapshot was created
```

### Learning Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `idea_confidence_versions` | История confidence | No (append-only) | Learning Loop API |
| `fatigue_state_versions` | История fatigue | No (append-only) | Learning Loop API |
| `component_learnings` | Learnings по компонентам | Yes | Learning Loop |
| `component_learning_snapshots` | Daily snapshots для drift detection | No (append-only) | MaintenanceWorkflow |
| `avatar_learnings` | Learnings по аватарам | Yes | Learning Loop |

### Buyer Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `buyers` | Зарегистрированные баеры | Yes | buyer_onboarding |
| `buyer_states` | Временное состояние онбординга | Yes | buyer_onboarding |
| `buyer_interactions` | Лог взаимодействий | No (append-only) | telegram_router |
| `historical_import_queue` | Очередь импорта | Yes | historical_loader |

### Config Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `config` | Конфигурация системы | Yes | manual |
| `keitaro_config` | Keitaro credentials | Yes | manual |
| `avatars` | Целевые аватары | Yes | manual |
| `event_log` | Лог событий | No (append-only) | all workflows |

### Recommendation & Exploration Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `recommendations` | Рекомендации для баеров | Yes (status) | recommendation_generator |
| `exploration_log` | Лог exploration решений | Yes (outcome) | exploration_tracker |
| `premises` | Narrative vehicles для гипотез | Yes (status) | premise_generator |
| `premise_learnings` | Learnings по premises | Yes | Learning Loop |
| `reminder_log` | Лог напоминаний | No (append-only) | reminder_workflow |

### Knowledge Extraction Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `knowledge_sources` | Исходные транскрипты (YouTube курсы и т.п.) | Yes (processed) | KnowledgeIngestionWorkflow |
| `knowledge_extractions` | Извлечённые знания (pending review) | Yes (status) | KnowledgeIngestionWorkflow, KnowledgeApplicationWorkflow |

**Колонки knowledge_sources:**
- `id` (UUID PK), `source_type` (youtube/file/manual), `title`, `url`, `transcript_text`
- `processed`, `processed_at`, `created_at`, `created_by`

**Колонки knowledge_extractions:**
- `id` (UUID PK), `source_id` (FK), `knowledge_type` (premise/creative_attribute/process_rule/component_weight)
- `name`, `description`, `payload` (JSONB), `confidence_score`, `supporting_quotes`
- `status` (pending/approved/rejected/applied), `reviewed_by`, `reviewed_at`
- `applied_at`, `applied_to`, `created_at`

### Inspiration System Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `staleness_snapshots` | Снимки метрик застоялости | No (append-only) | MaintenanceWorkflow |
| `external_inspirations` | Внешние креативы из spy tools | Yes (status) | external_inspiration_ingestion |

#### staleness_snapshots
```
id                        UUID      PK
diversity_score           NUMERIC        -- Уникальность компонентов (0-1)
win_rate_trend            NUMERIC        -- Тренд win_rate (negative = declining)
fatigue_ratio             NUMERIC        -- Доля идей с высоким fatigue
days_since_new_component  INT            -- Дней с последнего нового компонента
exploration_success_rate  NUMERIC        -- Успешность exploration
staleness_score           NUMERIC        -- Composite score
is_stale                  BOOLEAN        -- GENERATED: staleness_score > 0.6
avatar_id                 UUID           -- Контекст (NULL = global)
geo                       TEXT
action_taken              TEXT           -- none | cross_transfer | external_injection
created_at                TIMESTAMP
```

#### external_inspirations
```
id                   UUID      PK
source_type          TEXT           -- adheart | fb_spy | manual | competitor
source_url           TEXT
source_id            TEXT           -- External system ID
raw_creative_data    JSONB          -- Сырые данные от spy tool
extracted_components JSONB          -- LLM-извлечённые компоненты
vertical             TEXT
geo                  TEXT
status               TEXT           -- pending | extracted | injected | rejected | expired
injection_trigger    TEXT           -- Какой staleness signal триггернул
injected_components  JSONB
created_at           TIMESTAMP
```

#### component_learnings (origin columns)
```
origin_type        TEXT DEFAULT 'organic'  -- organic | cross_transfer | external_injection | manual
origin_source_id   UUID                    -- FK → external_inspirations.id
origin_segment     JSONB                   -- {avatar_id, geo} для cross_transfer
injected_at        TIMESTAMP
```

### Feature Engineering Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `feature_experiments` | Реестр экспериментальных ML фичей | Yes (status) | feature_registry |
| `derived_feature_values` | Вычисленные значения фичей | Yes (upsert) | feature_computation |

#### feature_experiments
```
id                     UUID      PK
name                   TEXT      UNIQUE NOT NULL
description            TEXT
sql_definition         TEXT      NOT NULL
status                 TEXT      DEFAULT 'shadow' CHECK (shadow|active|deprecated)
created_at             TIMESTAMP
activated_at           TIMESTAMP -- When promoted to active
deprecated_at          TIMESTAMP
deprecation_reason     TEXT
sample_size            INT       DEFAULT 0
correlation_cpa        NUMERIC   -- Correlation with CPA
correlation_updated_at TIMESTAMP
depends_on             TEXT[]    -- Feature dependencies
used_in                TEXT[]    -- Where feature is used
```

#### derived_feature_values
```
id           UUID      PK
feature_name TEXT      FK → feature_experiments.name ON DELETE CASCADE
entity_type  TEXT      CHECK (idea|outcome|creative)
entity_id    UUID
value        NUMERIC
computed_at  TIMESTAMP
UNIQUE (feature_name, entity_type, entity_id)
```

**Governance Rules:**
- `min_sample_size`: 100 — минимум для promotion
- `min_abs_correlation`: 0.08 — минимальная корреляция с CPA
- `max_active_features`: 10 — лимит активных фичей
- `deprecate_after_days`: 30 — автодепрекация

### Normalization Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `geo_lookup` | Нормализация гео (MX, DE, US...) | Yes | manual |
| `vertical_lookup` | Нормализация вертикалей (POT, WL...) | Yes | manual |

**Функции нормализации:**
- `normalize_geo(text)` → canonical geo code (e.g., "mexico" → "MX")
- `normalize_vertical(text)` → canonical vertical code (e.g., "потенция" → "POT")
- `normalize_geos(text[])` → normalized array of geo codes
- `normalize_verticals(text[])` → normalized array of vertical codes
- `create_buyer_normalized(...)` → создание баера с автонормализацией (поддерживает comma-separated values)

### Creatives Table Structure

```
creatives
├── id UUID (PK)
├── tracker_id TEXT
├── video_url TEXT
├── buyer_id UUID          FK → buyers.id
├── source_type TEXT       -- user | spy | system
├── tracking_status TEXT   -- pending | tracking | completed
├── test_budget NUMERIC
├── target_vertical TEXT   -- Target vertical (from buyer.verticals[0] at registration)
├── target_geo TEXT        -- Target geo (from buyer.geos[0] at registration)
├── status TEXT
└── created_at, updated_at
```

**target_vertical/target_geo** — контекст для какой вертикали/гео был создан креатив.
Значения берутся из `buyer.verticals[0]` и `buyer.geos[0]` в момент регистрации.
Для spy креативов может быть null если баер не имеет verticals/geos.

### Buyers Table Structure

```
buyers
├── id UUID (PK)
├── telegram_id TEXT (unique)
├── name TEXT
├── geos TEXT[]        -- Array of canonical geo codes: {MX, DE, US}
├── verticals TEXT[]   -- Array of canonical vertical codes: {POT, WL}
├── keitaro_source TEXT
├── status TEXT
└── created_at, updated_at
```

**Note:** Deprecated columns `geo` and `vertical` were removed in migration 026.

**Онбординг поддерживает ввод нескольких значений через запятую:**
- Гео: "DE, MX, US" → `{DE, MX, US}`
- Вертикали: "POT, WL" → `{POT, WL}`

---

## SQL Query Templates

### Get Creative Pipeline State

```sql
SELECT
    c.id as creative_id,
    c.tracker_id,
    c.status as creative_status,
    t.transcript_text IS NOT NULL as transcribed,
    dc.id IS NOT NULL as decomposed,
    i.id as idea_id,
    i.status as idea_status,
    d.decision,
    h.status as hypothesis_status,
    h.delivered_at
FROM genomai.creatives c
LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
LEFT JOIN genomai.decomposed_creatives dc ON dc.creative_id = c.id
LEFT JOIN genomai.ideas i ON dc.idea_id = i.id
LEFT JOIN genomai.decisions d ON d.idea_id = i.id
LEFT JOIN genomai.hypotheses h ON h.idea_id = i.id
ORDER BY c.created_at DESC
LIMIT 10;
```

### Get Idea with Confidence

```sql
SELECT
    i.id,
    i.canonical_hash,
    i.status,
    i.death_state,
    icv.confidence_value,
    icv.version
FROM genomai.ideas i
LEFT JOIN LATERAL (
    SELECT * FROM genomai.idea_confidence_versions
    WHERE idea_id = i.id
    ORDER BY version DESC LIMIT 1
) icv ON true
WHERE i.id = 'uuid-here';
```

### Get Decision with Trace

```sql
SELECT
    d.id,
    d.idea_id,
    d.decision,
    dt.checks,
    dt.result
FROM genomai.decisions d
JOIN genomai.decision_traces dt ON dt.decision_id = d.id
WHERE d.idea_id = 'uuid-here'
ORDER BY d.created_at DESC
LIMIT 1;
```

### Count by Status

```sql
SELECT
    'creatives' as entity,
    status,
    COUNT(*)
FROM genomai.creatives
GROUP BY status

UNION ALL

SELECT
    'ideas',
    status,
    COUNT(*)
FROM genomai.ideas
GROUP BY status

UNION ALL

SELECT
    'hypotheses',
    status,
    COUNT(*)
FROM genomai.hypotheses
GROUP BY status;
```

---

## Foreign Key Relationships

```
creatives
    └── transcripts.creative_id
    └── decomposed_creatives.creative_id
    │       └── ideas.id (via decomposed_creatives.idea_id)
    │               └── decisions.idea_id
    │               │       └── decision_traces.decision_id
    │               │       └── hypotheses.decision_id
    │               └── hypotheses.idea_id
    │               │       └── deliveries.idea_id
    │               └── outcome_aggregates.decision_id
    │               └── idea_confidence_versions.idea_id
    │               └── fatigue_state_versions.idea_id
    │               └── exploration_log.idea_id
    └── recommendations.creative_id (when recommendation executed)

buyers
    └── creatives.buyer_id
    └── hypotheses.buyer_id
    └── historical_import_queue.buyer_id
    └── recommendations.buyer_id
    └── reminder_log.buyer_id

avatars
    └── ideas.avatar_id
    └── avatar_learnings.avatar_id
    └── component_learnings.avatar_id
    └── exploration_log.avatar_id
    └── recommendations.avatar_id
    └── premise_learnings.avatar_id

premises
    └── hypotheses.premise_id
    └── premise_learnings.premise_id
```

---

## Detailed Table Structures

### recommendations
```
id                    UUID      PK
buyer_id              UUID      FK → buyers.id
avatar_id             UUID      FK → avatars.id
geo                   TEXT
vertical              TEXT
recommended_components JSONB    -- Components to use
mode                  TEXT      -- exploitation | exploration
exploration_type      TEXT
description           TEXT
status                TEXT      -- pending | sent | accepted | rejected | executed | expired
creative_id           UUID      FK → creatives.id (when executed)
was_successful        BOOLEAN
outcome_cpa           NUMERIC
confidence_scores     JSONB
telegram_message_id   TEXT
created_at            TIMESTAMPTZ
expires_at            TIMESTAMPTZ DEFAULT now() + 7 days
```

### premises
```
id                UUID      PK
premise_type      TEXT      -- method | discovery | confession | secret | ingredient | mechanism | breakthrough | transformation
name              TEXT
description       TEXT
origin_story      TEXT
mechanism_claim   TEXT
source            TEXT      -- manual | llm_generated | extracted
status            TEXT      -- active | emerging | fatigued | dead
vertical          TEXT
geo               TEXT
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

### outcome_aggregates
```
id                UUID      PK
creative_id       UUID      FK → creatives.id
decision_id       UUID      FK → decisions.id (required if origin_type='system')
window_id         TEXT      -- D1, D3, D7, D7+
window_start      DATE      -- Decision date
window_end        DATE      -- Snapshot date
impressions       INT
conversions       INT
spend             NUMERIC
cpa               NUMERIC   -- Cost Per Acquisition
trend             TEXT      -- improving | stable | declining
volatility        NUMERIC   -- Coefficient of variation (CV = std_dev / mean)
environment_ctx   JSONB
origin_type       TEXT      -- system | user
learning_applied  BOOLEAN
created_at        TIMESTAMPTZ
```

**volatility interpretation:**
- `< 0.1`: Low volatility (stable performance)
- `0.1-0.3`: Medium volatility
- `> 0.3`: High volatility (unstable performance)

### exploration_log
```
id                      UUID      PK
exploration_type        TEXT      -- new_avatar | new_component | mutation | random
idea_id                 UUID      FK → ideas.id
avatar_id               UUID      FK → avatars.id
component_type          TEXT
component_value         TEXT
geo                     TEXT
exploration_score       NUMERIC
exploitation_score      NUMERIC
sample_size_at_decision INT
was_successful          BOOLEAN
outcome_cpa             NUMERIC
outcome_spend           NUMERIC
outcome_revenue         NUMERIC
created_at              TIMESTAMPTZ
outcome_recorded_at     TIMESTAMPTZ
```

---

## Immutable Tables (No UPDATE/DELETE)

Эти таблицы имеют triggers, блокирующие UPDATE/DELETE:

- `decisions`
- `decision_traces`
- `transcripts`
- `outcome_aggregates` (UPDATE только для `learning_applied`)
- `daily_metrics_snapshot`
- `idea_confidence_versions`
- `fatigue_state_versions`
- `deliveries`
- `event_log`

**Для очистки используй TRUNCATE CASCADE, не DELETE.**

---

### Infrastructure Tables

#### agent_tasks (Multi-Agent Orchestration, Issue #350)

Centralized task queue for multi-agent coordination.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `issue_number` | INT | GitHub issue number (UNIQUE) |
| `issue_title` | TEXT | Issue title |
| `status` | TEXT | pending/claimed/completed/abandoned |
| `claimed_by` | TEXT | Agent ID that claimed the task |
| `claimed_at` | TIMESTAMPTZ | When claimed |
| `completed_at` | TIMESTAMPTZ | When completed |
| `last_heartbeat` | TIMESTAMPTZ | Last heartbeat timestamp |
| `priority` | INT | Task priority (higher = more important) |
| `created_at` | TIMESTAMPTZ | Created timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

**Functions:**
- `claim_agent_task(issue_number, agent_id)` → BOOLEAN
- `heartbeat_agent_task(issue_number, agent_id)` → BOOLEAN
- `complete_agent_task(issue_number, agent_id)` → BOOLEAN
- `release_orphaned_tasks(timeout_minutes)` → INT

---

## Schema Version

Current: genomai schema v1.4.0 (Release 2026-01-11)

**Changes in v1.4.0:**
- `agent_tasks`: New table for multi-agent coordination (#350)
- Functions: `claim_agent_task`, `heartbeat_agent_task`, `complete_agent_task`, `release_orphaned_tasks`
- `MaintenanceWorkflow`: Added orphan detection step

**Changes in v1.3.0:**
- `buyers`: Removed deprecated columns `geo` and `vertical` (migration 026)
- Code now uses `geos[]` and `verticals[]` arrays exclusively

**Changes in v1.2.0:**
- `creatives`: Added `target_vertical` and `target_geo` columns (#193)
- Index `idx_creatives_target` on (target_vertical, target_geo)

**Changes in v1.1.0:**
- `raw_metrics_current`: Changed to tracker_id (PK), date, metrics (JSONB), updated_at
- `daily_metrics_snapshot`: Changed to tracker_id, date, metrics (JSONB), created_at
- Added tables: `recommendations`, `premises`, `premise_learnings`, `exploration_log`, `reminder_log`
- Updated FK relationships for new tables
