# QA Notes: Issue #301 - Inspiration System

## Summary
Реализована система предотвращения деградации креативов (инбридинга).

## Changes

### New Files
- `src/services/staleness_detector.py` - детекция застоялости системы
- `src/services/cross_transfer.py` - перенос компонентов между сегментами
- `src/services/external_inspiration.py` - обработка внешних креативов
- `infrastructure/migrations/028_inspiration_system.sql` - таблицы staleness_snapshots, external_inspirations
- `infrastructure/migrations/029_component_learnings_origin.sql` - origin columns для component_learnings

### Modified Files
- `temporal/workflows/maintenance.py` - добавлен шаг staleness detection
- `temporal/activities/maintenance.py` - добавлена activity check_staleness
- `src/services/recommendation.py` - добавлен cross-transfer (10% exploration)

## Database Changes
- `genomai.staleness_snapshots` - снимки метрик застоялости
- `genomai.external_inspirations` - внешние креативы из spy tools
- `genomai.component_learnings` - новые колонки origin_type, origin_source_id, origin_segment, injected_at

## Test Plan

### Phase 1: Staleness Detection
```sql
-- Проверить что таблица создана
SELECT COUNT(*) FROM genomai.staleness_snapshots;

-- Trigger MaintenanceWorkflow и проверить snapshot
python3 -m temporal.schedules trigger maintenance
```

### Phase 2: Cross-Segment Transfer
```sql
-- После рекомендации с cross-transfer
SELECT * FROM genomai.component_learnings
WHERE origin_type = 'cross_transfer';
```

### Phase 3: External Inspiration
```sql
-- После manual ingestion
SELECT status, COUNT(*) FROM genomai.external_inspirations GROUP BY status;
```

## Architecture

```
Recommendation Flow:
75% exploitation → best win_rate
15% Thompson Sampling → existing components
10% cross-transfer → components from other segments

Staleness Detection (every 6h via MaintenanceWorkflow):
1. Calculate metrics (diversity, win_rate_trend, fatigue, etc.)
2. Compute staleness_score (weighted average)
3. If stale (>0.6) → log warning, recommend action

External Inspiration (manual/webhook):
1. Ingest raw creative data
2. LLM extracts components
3. On staleness trigger → inject into component_learnings
```

## Key Insight
Инжекция через Thompson Sampling: компонент с sample_size=0 имеет Beta(1,1) = максимальная неопределённость → высокий шанс быть выбранным при exploration. Система сама тестирует, не нужен хардкод "продвижения".
