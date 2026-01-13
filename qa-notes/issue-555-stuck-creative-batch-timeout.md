# Issue #555: No timeout на stuck creative recovery в maintenance

## Что изменено

- Добавлена константа `MAX_BATCH_SIZE = 50` для ограничения обработки за один запуск
- Добавлены поля `_processed_stuck_ids`, `_processed_failed_ids` в `MaintenanceInput` для отслеживания обработанных creatives
- Добавлены поля `_accumulated_*` для сохранения счётчиков между continue-as-new
- Step 9 (stuck creatives recovery): добавлен батчинг и фильтрация уже обработанных
- Step 10 (failed creatives retry): добавлен батчинг и фильтрация уже обработанных
- Добавлена логика continue-as-new в конце workflow для обработки оставшихся creatives

## Как это работает

1. Workflow получает список stuck/failed creatives
2. Фильтрует уже обработанные (из `_processed_*_ids`)
3. Обрабатывает батч из максимум 50 элементов
4. Если остались необработанные — устанавливает `needs_continuation = True`
5. В конце workflow, если `needs_continuation` — вызывает `continue_as_new(input)` с обновлённым состоянием
6. Новый execution продолжает с того места, где остановился предыдущий

## Test

```bash
cd decision-engine-service && python3 -c "
from temporal.workflows.maintenance import MaintenanceInput, MAX_BATCH_SIZE
# Check MAX_BATCH_SIZE exists and is reasonable
assert MAX_BATCH_SIZE == 50, f'Expected 50, got {MAX_BATCH_SIZE}'
# Check new fields in MaintenanceInput
inp = MaintenanceInput()
assert hasattr(inp, '_processed_stuck_ids'), 'Missing _processed_stuck_ids'
assert hasattr(inp, '_processed_failed_ids'), 'Missing _processed_failed_ids'
assert hasattr(inp, '_accumulated_stuck_recovered'), 'Missing _accumulated_stuck_recovered'
assert inp._processed_stuck_ids == [], 'Default should be empty list'
print('OK: Batching support verified')
"
```
