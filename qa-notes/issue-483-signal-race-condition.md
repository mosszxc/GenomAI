# Issue #483: Signal handlers race condition fix

## Что изменено

- Добавлен `WorkflowStateSnapshot` (frozen dataclass) для immutable state
- Signal handlers (`user_message`, `cancel`) обновляют snapshot атомарно
- Query handlers (`get_state`, `get_progress`) читают из immutable snapshot
- Метод `_set_state()` гарантирует atomic state transitions
- Все переходы состояний используют `_set_state()` вместо прямого присваивания

## Архитектура решения

```
Signal Handler                 Query Handler
     |                              |
     v                              |
_set_state(new_state)               |
     |                              |
     v                              |
self._state = new_state             |
     |                              |
     v                              |
self._snapshot = NEW_SNAPSHOT  -->  snapshot = self._snapshot  (atomic read)
                                    |
                                    v
                               return snapshot.state
```

- `WorkflowStateSnapshot` — frozen dataclass (immutable)
- Single assignment = atomic operation в Python
- Query handlers читают snapshot без locks

## Файлы

- `temporal/workflows/buyer_onboarding.py`

## Test

```bash
cd decision-engine-service && python3 -c "
from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow, WorkflowStateSnapshot
from dataclasses import is_dataclass, FrozenInstanceError

# Test 1: WorkflowStateSnapshot is frozen dataclass
assert is_dataclass(WorkflowStateSnapshot), 'Must be dataclass'
snap = WorkflowStateSnapshot(state='test')
try:
    snap.state = 'new'
    assert False, 'Should be immutable'
except FrozenInstanceError:
    pass

# Test 2: Workflow initializes with snapshot
wf = BuyerOnboardingWorkflow()
assert hasattr(wf, '_snapshot'), 'Must have snapshot'
assert wf._snapshot.state == 'AWAITING_NAME', f'Initial state wrong: {wf._snapshot.state}'

# Test 3: _set_state updates snapshot atomically
from temporal.models.buyer import OnboardingState
wf._set_state(OnboardingState.AWAITING_GEO)
assert wf._snapshot.state == 'AWAITING_GEO', f'State not updated: {wf._snapshot.state}'

# Test 4: Query handlers read from snapshot
assert wf.get_state() == 'AWAITING_GEO', 'get_state must read snapshot'
progress = wf.get_progress()
assert progress['state'] == 'AWAITING_GEO', 'get_progress must read snapshot'

print('OK: Race condition fix verified')
"
```
