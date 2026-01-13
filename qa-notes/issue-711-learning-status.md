# Issue #711: /learning/status endpoint не работает (404)

## Что изменено
- Убрана авторизация с `/learning/status` endpoint (сделан публичным)
- Добавлено поле `last_processed_at` в ответ
- Добавлена функция `fetch_last_processed_at()` в learning_loop.py

## Изменённые файлы
- `decision-engine-service/src/routes/learning.py` - endpoint теперь публичный
- `decision-engine-service/src/services/learning_loop.py` - новая функция fetch_last_processed_at

## Test

```bash
curl -sf localhost:10000/learning/status
```
