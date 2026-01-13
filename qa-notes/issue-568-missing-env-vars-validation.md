# Issue #568: Missing env vars validation в temporal/config.py

## Что изменено
- Добавлена функция `get_required_env()` для fail-fast валидации обязательных переменных
- `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY` теперь проверяются при старте
- При отсутствии переменных сервис падает сразу с понятной ошибкой

## Файлы
- `decision-engine-service/temporal/config.py`

## Test
```bash
cd decision-engine-service && python3 -c "from temporal.config import get_required_env; get_required_env('NONEXISTENT_VAR')" 2>&1 | grep -q "NONEXISTENT_VAR is not set" && echo "OK: validation works"
```
