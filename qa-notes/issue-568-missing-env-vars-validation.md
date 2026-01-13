# Issue #568: Missing env vars validation в temporal/config.py

## Что изменено
- Добавлена функция `get_required_env()` для fail-fast валидации обязательных переменных
- `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY` теперь проверяются при старте
- При отсутствии переменных сервис падает сразу с понятной ошибкой
- В тестовом окружении (pytest) валидация пропускается

## Файлы
- `decision-engine-service/temporal/config.py`

## Test
```bash
grep -q "get_required_env.*SUPABASE_URL" decision-engine-service/temporal/config.py && grep -q "get_required_env.*SUPABASE_SERVICE_ROLE_KEY" decision-engine-service/temporal/config.py && echo "OK: validation applied"
```
