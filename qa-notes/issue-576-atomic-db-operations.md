# Issue #576: Atomic DB Operations

## Что изменено

Исправлена проблема с цепочками DB операций без транзакций, которая могла приводить к inconsistent state.

### Затронутые места и решения:

1. **create_idea / upsert_idea** (`temporal/activities/supabase.py`)
   - Было: INSERT idea + PATCH decomposed_creative как отдельные операции
   - Стало: Единая RPC функция `create_idea_with_link` / `upsert_idea_with_link`
   - Если PATCH упадёт, INSERT откатывается

2. **process_single_outcome** (`src/services/learning_loop.py`)
   - Было: 5 отдельных операций (confidence, fatigue, death_state, mark_processed, event)
   - Стало: Единая RPC функция `apply_learning_atomic`
   - Все операции в одной транзакции

### Новые RPC функции (migration 045):

```sql
-- Atomic idea creation with decomposed_creative link
genomai.create_idea_with_link(p_idea_id, p_canonical_hash, p_avatar_id, p_decomposed_creative_id)

-- Atomic upsert idea (TOCTOU-safe)
genomai.upsert_idea_with_link(p_idea_id, p_canonical_hash, p_avatar_id, p_decomposed_creative_id)

-- Atomic learning application (5 operations)
genomai.apply_learning_atomic(p_idea_id, p_outcome_id, p_new_confidence, ...)
```

## Test

```bash
grep -q "apply_learning_atomic_rpc" decision-engine-service/src/services/learning_loop.py && grep -q "create_idea_with_link" infrastructure/migrations/045_atomic_idea_learning.sql && echo "OK: Atomic operations implemented"
```

## Файлы

- `infrastructure/migrations/045_atomic_idea_learning.sql` - RPC функции
- `decision-engine-service/temporal/activities/supabase.py` - create_idea, upsert_idea
- `decision-engine-service/src/services/learning_loop.py` - apply_learning_atomic_rpc, process_single_outcome
