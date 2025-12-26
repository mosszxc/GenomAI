# Schema Reference

Единый источник истины для схемы БД GenomAI.

**Last updated:** 2025-12-26

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
| `decision_traces` | Trace решений | No (append-only) | Decision Engine API |
| `hypotheses` | Генерированные гипотезы | Yes (status) | hypothesis_factory |
| `deliveries` | Лог доставок | No (append-only) | telegram_delivery |

### Metrics Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `raw_metrics_current` | Текущие метрики | Yes (update) | keitaro_poller |
| `daily_metrics_snapshot` | Daily snapshots | No (append-only) | snapshot_creator |
| `outcome_aggregates` | Агрегированные outcomes | Yes (learning_applied) | outcome_aggregator |

### Learning Tables

| Table | Purpose | Mutable | Writer |
|-------|---------|---------|--------|
| `idea_confidence_versions` | История confidence | No (append-only) | Learning Loop API |
| `fatigue_state_versions` | История fatigue | No (append-only) | Learning Loop API |
| `component_learnings` | Learnings по компонентам | Yes | Learning Loop |
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
            └── ideas.id (via decomposed_creatives.idea_id)
                    └── decisions.idea_id
                    │       └── decision_traces.decision_id
                    │       └── hypotheses.decision_id
                    └── hypotheses.idea_id
                    │       └── deliveries.idea_id
                    └── outcome_aggregates.decision_id
                    └── idea_confidence_versions.idea_id
                    └── fatigue_state_versions.idea_id

buyers
    └── creatives.buyer_id
    └── hypotheses.buyer_id
    └── historical_import_queue.buyer_id

avatars
    └── ideas.avatar_id
    └── avatar_learnings.avatar_id
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

## Schema Version

Current: genomai schema v1.0.0 (Release 2025-12-26)
