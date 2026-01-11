# QA Notes: DB Cleanup - Deprecated Columns

**Date:** 2026-01-10
**Task:** Очистка БД от неиспользуемых элементов

## Summary

Проведён аудит схемы БД genomai. Выявлены и исправлены deprecated столбцы.

## Changes Made

### 1. Code Changes

**File:** `decision-engine-service/src/services/idea_registry.py` (lines 324-328)
- Заменено использование deprecated `buyer.geo` / `buyer.vertical`
- Теперь используется `buyer.geos[0]` / `buyer.verticals[0]`

**File:** `decision-engine-service/temporal/workflows/recommendation.py` (lines 116-120)
- Убран fallback на deprecated поля
- Теперь напрямую читает из массивов `geos[]` / `verticals[]`

### 2. Migration

**File:** `infrastructure/migrations/026_drop_deprecated_buyer_columns.sql`
- `ALTER TABLE genomai.buyers DROP COLUMN IF EXISTS geo`
- `ALTER TABLE genomai.buyers DROP COLUMN IF EXISTS vertical`
- Verification block для проверки успешного удаления

### 3. Documentation

**File:** `docs/SCHEMA_REFERENCE.md`
- Обновлена структура таблицы buyers (убраны deprecated колонки)
- Обновлена версия схемы до v1.3.0

## Testing

```bash
# Import verification
cd decision-engine-service
python3 -c "from src.services.idea_registry import *; print('OK')"
python3 -c "from temporal.workflows.recommendation import *; print('OK')"
```

**Result:** PASSED

## Tables Analysis

| Category | Tables |
|----------|--------|
| **Used in code** | creatives, ideas, decomposed_creatives, decisions, decision_traces, buyers, buyer_states, buyer_interactions, historical_import_queue, raw_metrics_current, daily_metrics_snapshot, outcome_aggregates, idea_confidence_versions, fatigue_state_versions, component_learnings, avatars, event_log, recommendations, exploration_log, premises, premise_learnings, hypotheses |
| **Used via N8N** | transcripts, deliveries |
| **Config (manual)** | config, keitaro_config, geo_lookup, vertical_lookup |
| **Unused (kept for future)** | avatar_learnings, reminder_log |

## Files Changed

1. `decision-engine-service/src/services/idea_registry.py`
2. `decision-engine-service/temporal/workflows/recommendation.py`
3. `infrastructure/migrations/026_drop_deprecated_buyer_columns.sql` (NEW)
4. `docs/SCHEMA_REFERENCE.md`
