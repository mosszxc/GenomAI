# Issue #568: Missing env vars validation в temporal/config.py

## Что изменено
- Добавлена функция `get_required_env()` для fail-fast валидации обязательных переменных
- `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY` теперь проверяются при старте
- При отсутствии переменных сервис падает сразу с понятной ошибкой

## Файлы
- `decision-engine-service/temporal/config.py`

## Test
```bash
cd decision-engine-service && python3 -c "import sys; sys.path.insert(0,'.'); exec(open('temporal/config.py').read().split('settings = ')[0]); get_required_env('MISSING_VAR')" 2>&1 | grep -q "MISSING_VAR is not set" && echo "OK: validation works"
```
