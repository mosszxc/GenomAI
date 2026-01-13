# Issue #727: /learning/status возвращает 200 с невалидным токеном

## Что изменено
- Добавлена проверка авторизации (`verify_api_key`) к эндпоинту `/learning/status`
- Теперь эндпоинт требует валидный API ключ в заголовке Authorization
- Убрана пометка "(public endpoint)" из docstring

## Файлы
- `decision-engine-service/src/routes/learning.py`

## Test
```bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer invalid-token-12345" localhost:10000/learning/status) && [ "$STATUS" = "401" ] && echo "OK: returns 401 for invalid token" || (echo "FAIL: expected 401, got $STATUS" && exit 1)
```

## Безопасность
- `/learning/status` теперь защищён авторизацией
- Исключена утечка информации о состоянии системы неавторизованным пользователям
