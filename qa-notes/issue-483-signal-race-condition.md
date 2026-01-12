# Issue #483: Signal handlers race condition

## Что изменено

- `get_progress()` query handler теперь возвращает копии списков `geos` и `verticals` через `list()`
- Это предотвращает race condition при одновременном чтении/записи
- Также защищает от случайной мутации внутреннего состояния workflow через возвращённый dict

## Файлы

- `temporal/workflows/buyer_onboarding.py:742-759`

## Test

```bash
(cd decision-engine-service && python3 -c "from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow; w = BuyerOnboardingWorkflow(); w._geos = ['US', 'UK']; progress = w.get_progress(); progress['geos'].append('DE'); assert w._geos == ['US', 'UK'], f'Mutated: {w._geos}'; print('OK: internal state protected')")
```
