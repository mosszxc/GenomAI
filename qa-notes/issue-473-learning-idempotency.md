# Issue #473: Learning Loop Idempotency Fix

## Проблема

Activity `process_learning_batch` не была идемпотентной. При retry обрабатывала те же outcomes повторно, что приводило к дубликатам confidence/fatigue versions.

**Сценарий:**
1. Activity обрабатывает 100 outcomes
2. Обновляет confidence versions, fatigue
3. Worker crash **перед return результата**
4. Temporal retries activity
5. **Те же 100 outcomes обрабатываются снова**
6. Confidence versions удваиваются

**Impact:**
- Duplicate confidence versions в БД
- Learning metrics double-counted
- Неверные решения Decision Engine

## Решение

### 1. Database Layer (миграция 039)

Unique index на `source_outcome_id`:
```sql
CREATE UNIQUE INDEX idx_idea_confidence_versions_outcome_unique
ON idea_confidence_versions(source_outcome_id);

CREATE UNIQUE INDEX idx_fatigue_state_versions_outcome_unique
ON fatigue_state_versions(source_outcome_id);
```

### 2. Application Layer

**`is_outcome_already_processed()`** - проверка перед обработкой:
- Ищет existing confidence_version с данным source_outcome_id
- Если найден → outcome уже обработан

**`process_single_outcome()`** - early return для duplicates:
- Вызывает `is_outcome_already_processed()` в начале
- Возвращает `{"skipped": True}` если уже обработан
- Также помечает outcome как `learning_applied=true` (на случай если флаг не был установлен)

### 3. Tracking

- `LearningResult.skipped_count` - счётчик пропущенных (idempotent) outcomes
- Логирование в workflow: "X processed, Y skipped (idempotent)"

## Изменённые файлы

- `infrastructure/migrations/039_learning_idempotency.sql`
- `supabase/migrations/20240101003900_learning_idempotency.sql`
- `decision-engine-service/src/services/learning_loop.py`
- `decision-engine-service/temporal/activities/learning.py`
- `decision-engine-service/temporal/workflows/learning_loop.py`
- `decision-engine-service/tests/unit/test_learning_idempotency.py`

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-473-arch-critical-learning-loop-не-идемпотен/decision-engine-service && python3 -m pytest tests/unit/test_learning_idempotency.py -v
```

## Проверка дубликатов в БД

После применения миграции проверить отсутствие дубликатов:
```sql
SELECT source_outcome_id, COUNT(*)
FROM genomai.idea_confidence_versions
GROUP BY source_outcome_id
HAVING COUNT(*) > 1;
-- Должно вернуть 0 строк
```
