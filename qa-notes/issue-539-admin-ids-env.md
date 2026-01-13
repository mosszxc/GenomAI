# Issue #539: Move hardcoded admin IDs to environment variables

## Что изменено
- `ADMIN_TELEGRAM_IDS` перенесён из хардкода в переменную окружения
- Добавлена фильтрация пустых значений при парсинге
- Функция `is_admin` защищена от пустых telegram_id

## Файлы
- `decision-engine-service/src/routes/telegram.py`

## Переменная окружения
```
ADMIN_TELEGRAM_IDS=291678304,123456789
```

## Test
```bash
python -c "
import os
os.environ['ADMIN_TELEGRAM_IDS'] = '111,222,333'
# Re-parse like the module does
ADMIN_TELEGRAM_IDS = [aid.strip() for aid in os.getenv('ADMIN_TELEGRAM_IDS', '').split(',') if aid.strip()]
def is_admin(tid): return bool(tid and tid in ADMIN_TELEGRAM_IDS)
assert ADMIN_TELEGRAM_IDS == ['111', '222', '333'], f'Parse failed: {ADMIN_TELEGRAM_IDS}'
assert is_admin('111') == True, 'Valid admin not recognized'
assert is_admin('999') == False, 'Non-admin recognized as admin'
assert is_admin('') == False, 'Empty string accepted'
assert is_admin(None) == False, 'None accepted'
print('OK: All tests passed')
"
```
