# Filter orphan stuck creatives

## Что изменено
- Добавлена фильтрация orphan креативов в `find_stuck_creatives` activity
- Креативы без событий в `event_log` теперь не считаются "stuck"
- Orphan данные (тестовые данные созданные напрямую в БД) игнорируются

## Проблема
Алерт ложно срабатывал на тестовые данные:
- Креативы/транскрипты созданы напрямую в БД
- Workflow никогда не запускался → нет событий в event_log
- Алерт считал их "stuck in decomposition"

## Решение
Добавлена проверка event_log:
- Если есть события → реально stuck
- Если нет событий → orphan data (игнорируем)

## Файлы
- `decision-engine-service/temporal/activities/maintenance.py`

## Test
```bash
curl -sf localhost:10000/health && echo "OK: server running"
```
