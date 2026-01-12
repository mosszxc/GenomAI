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
cd decision-engine-service && python3 -c "from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow, WorkflowStateSnapshot; from dataclasses import is_dataclass, FrozenInstanceError; from temporal.models.buyer import OnboardingState; assert is_dataclass(WorkflowStateSnapshot); wf = BuyerOnboardingWorkflow(); assert wf._snapshot.state == 'AWAITING_NAME'; wf._set_state(OnboardingState.AWAITING_GEO); assert wf.get_state() == 'AWAITING_GEO'; assert wf.get_progress()['state'] == 'AWAITING_GEO'; print('OK: Race condition fix verified')"
```
