# Issue #285: Temporal CLI подключается к Temporal Cloud локально

## Проблема
`python -m temporal.schedules list` падал с ошибкой:
```
RuntimeError: Failed client connect: Server connection error
127.0.0.1:7233, Connection refused
```

## Причина
1. `temporal/config.py` не загружал `.env` файл автоматически
2. Код `list_schedules()` использовал устаревший API Temporal SDK

## Решение

### 1. Автозагрузка .env
`config.py:27-35` - добавлен опциональный `load_dotenv()`:
```python
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass
```

### 2. Исправление Temporal SDK API
`schedules.py:151-171` - исправлены атрибуты:
- `client.list_schedules()` → `await client.list_schedules()`
- `schedule.info.schedule.state.note` → удалено (недоступно в ScheduleListInfo)
- `recent_actions[0].start_time` → `recent_actions[0].started_at`

## Тест
```bash
cd decision-engine-service
python3 -m temporal.schedules list
# Found 5 schedules: maintenance, daily-recommendations, learning-loop, metrics-processor, keitaro-poller

python3 -m temporal.schedules trigger learning-loop
# Triggered schedule: learning-loop
```

## Изменённые файлы
- `decision-engine-service/temporal/config.py` - автозагрузка .env
- `decision-engine-service/temporal/schedules.py` - исправление API

## Требования
- `python-dotenv` должен быть установлен: `pip install python-dotenv`
- `.env` файл с Temporal Cloud credentials в `decision-engine-service/`
