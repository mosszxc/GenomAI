# Issue #573 - Query params limit без max ограничения

## Что изменено

- Добавлена валидация `ge=1, le=1000` для параметра `limit` в 3 API endpoints:
  - `GET /premise/top` (limit default=10)
  - `GET /premise/active` (limit default=50)
  - `GET /api/knowledge/extractions` (limit default=20)

## Затронутые файлы

- `decision-engine-service/src/routes/premise.py`
- `decision-engine-service/src/routes/knowledge.py`

## Test

```bash
curl -sf "localhost:10000/premise/top?limit=9999" -H "Authorization: Bearer $API_KEY" && echo "FAIL: should reject" || echo "OK: rejected limit > 1000"
```
