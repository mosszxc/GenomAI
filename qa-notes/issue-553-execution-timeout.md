# Issue #553: Бесконечный retry без time bound в keitaro_polling

## Что изменено

- Добавлен `execution_timeout` для всех scheduled workflows в `temporal/schedules.py`:
  - `keitaro-poller`: 30 минут (interval 1 час)
  - `daily-recommendations`: 30 минут (daily cron)
  - `maintenance`: 1 час (interval 6 часов)
  - `health-check`: 15 минут (interval 3 часа)
- `ScheduleActionStartWorkflow` теперь передаёт `execution_timeout` при создании schedule

## Почему это важно

Без `execution_timeout` workflow с retry policy мог работать бесконечно при постоянных ошибках,
блокируя worker и накапливая ресурсы.

## Test

```bash
cd decision-engine-service && python3 -c "
from temporal.schedules import SCHEDULES
errors = []
for name, config in SCHEDULES.items():
    timeout = config.get('execution_timeout')
    if not timeout:
        errors.append(f'{name}: missing execution_timeout')
if errors:
    print('FAIL:', errors)
    exit(1)
print('OK: all schedules have execution_timeout')
"
```
