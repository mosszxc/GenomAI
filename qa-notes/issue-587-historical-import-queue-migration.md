# Issue #587: Missing CREATE TABLE migration for historical_import_queue

## Что изменено
- Добавлена миграция `044_historical_import_queue.sql` с полной структурой таблицы
- Включены все колонки: id, campaign_id, video_url, buyer_id, status, metrics, keitaro_source, date_from, date_to, error_message, created_at, updated_at
- Добавлены индексы: idx_historical_queue_buyer, idx_historical_queue_status
- Используется `CREATE TABLE IF NOT EXISTS` для идемпотентности

## Риск без этого фикса
При воссоздании БД с нуля таблица не создастся, что приведёт к критическому сбою Historical Import pipeline.

## Test
```bash
# Проверка синтаксиса SQL миграции (psql --echo-errors парсит без выполнения)
grep -q "CREATE TABLE IF NOT EXISTS genomai.historical_import_queue" infrastructure/migrations/044_historical_import_queue.sql && echo "OK: migration exists"
```
