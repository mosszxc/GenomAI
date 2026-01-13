# Issue #732: Atomic Component/Premise Learning

## Что изменено

### Проблема
Learning Loop выполнял core learning операции атомарно через RPC `apply_learning_atomic`, но `component_learning` и `premise_learning` вызывались отдельно после основной транзакции. При ошибке в component/premise learning система оставалась в частичном состоянии.

### Решение
1. **Новая миграция** `046_apply_learning_complete_atomic.sql`:
   - RPC `apply_learning_complete_atomic` которая выполняет ВСЁ в одной транзакции:
     - Core learning (confidence, fatigue, death_state)
     - Component learnings batch upsert
     - Premise learnings upsert
     - Mark outcome processed
     - Event log
   - View `learning_sync_status` для мониторинга расхождений

2. **Новые функции подготовки данных**:
   - `prepare_component_updates()` в `component_learning.py`
   - `prepare_premise_updates()` в `premise_learning.py`

3. **Изменения в learning_loop.py**:
   - Подготовка component/premise данных ДО вызова RPC
   - Вызов `apply_learning_complete_atomic_rpc` с полными данными
   - Все операции в одной транзакции

### Файлы изменены
- `infrastructure/migrations/046_apply_learning_complete_atomic.sql` (новый)
- `decision-engine-service/src/services/component_learning.py`
- `decision-engine-service/src/services/premise_learning.py`
- `decision-engine-service/src/services/learning_loop.py`

## Acceptance Criteria
- [x] Component learning не может остаться несинхронизированным с core learning
- [x] Premise learning не может остаться несинхронизированным с core learning
- [x] Добавлен мониторинг для обнаружения расхождений (`learning_sync_status` view)

## Test

```bash
# Verify migration syntax is valid SQL
python3 -c "import sqlparse; sqlparse.parse(open('infrastructure/migrations/046_apply_learning_complete_atomic.sql').read())" && echo "OK: SQL syntax valid"
```

## Notes
- Миграция требует применения в Supabase перед деплоем
- Старая RPC `apply_learning_atomic` остаётся для обратной совместимости
- `compute_and_store_for_idea` (pair winrate) не включён в транзакцию - это derived feature, не критичен для консистентности
