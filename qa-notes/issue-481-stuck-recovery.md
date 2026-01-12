# Issue #481: Stuck creative recovery

## Проблема

Maintenance workflow находил stuck creatives, но не восстанавливал их:
- Просто логировал и считал
- Не отменял зависшие workflows
- Не сбрасывал статус creatives
- Не перезапускал обработку

## Решение

1. Добавлены activities:
   - `cancel_stuck_creative_workflow` - отменяет зависший Temporal workflow
   - `reset_creative_for_recovery` - сбрасывает статус creative на `registered`

2. Добавлен параметр `stuck_recovery_force_threshold_minutes` (default: 120)

3. Обновлена логика Step 10 в MaintenanceWorkflow:
   - Если creative stuck < 2 часов: попытка запустить новый workflow (ALLOW_DUPLICATE_FAILED_ONLY)
   - Если creative stuck >= 2 часов: force recovery (cancel -> reset -> restart)

4. `find_stuck_creatives` теперь возвращает `stuck_duration_minutes`

## Файлы изменены

- `temporal/activities/maintenance.py`:
  - Добавлен import `TemporalClient`
  - Добавлена функция `_calculate_stuck_duration_minutes`
  - Добавлена activity `cancel_stuck_creative_workflow`
  - Добавлена activity `reset_creative_for_recovery`
  - Обновлен `find_stuck_creatives` с `stuck_duration_minutes`

- `temporal/workflows/maintenance.py`:
  - Добавлен import новых activities
  - Добавлен параметр `stuck_recovery_force_threshold_minutes`
  - Обновлен Step 10 с логикой force recovery

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-481-arch-high-stuck-creative-recovery-только/decision-engine-service && python3 -c "
from temporal.activities.maintenance import (
    cancel_stuck_creative_workflow,
    reset_creative_for_recovery,
    find_stuck_creatives,
    _calculate_stuck_duration_minutes,
)
from temporal.workflows.maintenance import MaintenanceInput, MaintenanceWorkflow

# Test 1: _calculate_stuck_duration_minutes
from datetime import datetime, timedelta
old_ts = (datetime.utcnow() - timedelta(minutes=150)).isoformat()
duration = _calculate_stuck_duration_minutes(old_ts)
assert 145 <= duration <= 155, f'Duration {duration} not in expected range'

# Test 2: MaintenanceInput has new field
inp = MaintenanceInput()
assert hasattr(inp, 'stuck_recovery_force_threshold_minutes'), 'Missing threshold field'
assert inp.stuck_recovery_force_threshold_minutes == 120, 'Wrong default threshold'

# Test 3: Activities exist and are callable
assert callable(cancel_stuck_creative_workflow), 'cancel_stuck_creative_workflow not callable'
assert callable(reset_creative_for_recovery), 'reset_creative_for_recovery not callable'

print('OK: All tests passed')
"
```
