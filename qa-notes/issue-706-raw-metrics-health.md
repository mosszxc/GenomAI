## Что изменено

Issue #706: `/health/metrics` возвращал 404 при попытке обратиться к таблице `raw_metrics_current`.

**Причина:** PostgREST возвращает 404 при обращении к таблице напрямую (возможно проблема с schema cache).

**Решение:**
1. Создана RPC функция `genomai.get_metrics_staleness()` для надёжного доступа к данным
2. Изменён `circuit_breaker.py` — использует RPC вместо прямого запроса к таблице

## Файлы

- `infrastructure/migrations/047_raw_metrics_genomai_schema.sql` — миграция с RPC функцией
- `decision-engine-service/temporal/circuit_breaker.py` — изменён `get_metrics_staleness()`

## Применение миграции

**ВАЖНО:** Перед тестированием применить миграцию в Supabase:

1. Открыть https://supabase.com/dashboard/project/ftrerelppsnbdcmtcwya/sql/new
2. Скопировать содержимое `infrastructure/migrations/047_raw_metrics_genomai_schema.sql`
3. Выполнить SQL

## Test

```bash
curl -sf localhost:10000/health/metrics | grep -q '"status"' && echo "OK: endpoint works" || echo "FAIL"
```
