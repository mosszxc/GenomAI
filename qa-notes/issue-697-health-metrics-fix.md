# Issue #697: fix(health): remove raw_metrics_current dependency

## Что изменено

- Добавлен `Accept-Profile: genomai` заголовок в `circuit_breaker.py` для запросов к Supabase
- Добавлен `Content-Profile: genomai` для write-запросов
- Исправлена ошибка 404 при запросе `/health/metrics` - таблица `raw_metrics_current` находится в схеме `genomai`, но заголовок схемы отсутствовал

## Причина

Функция `_get_headers()` не включала заголовки `Accept-Profile` и `Content-Profile`, необходимые для доступа к таблицам в схеме `genomai`. PostgREST по умолчанию искал таблицу в схеме `public`.

## Test

```bash
curl -sf localhost:10000/health/metrics | jq -e '.status != null' && echo "OK: endpoint works"
```
