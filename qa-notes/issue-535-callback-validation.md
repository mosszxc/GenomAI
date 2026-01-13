# Issue #535 - Callback query input injection vulnerability

## Что изменено

- Добавлена строгая валидация типов в `parse_callback_data()`:
  - `ke_approve_`, `ke_reject_`, `ke_skip_` - проверка UUID формата
  - `chat_` - проверка числового telegram_id
- Импортирован модуль `uuid` для валидации
- Логирование при невалидных данных (уже было)

## Локация

`decision-engine-service/src/routes/telegram.py:156-164`

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-535--callback-query-input-injection-vulnerab && PYTHONPATH=decision-engine-service python3 -c "
from src.routes.telegram import parse_callback_data, CallbackDataError
import sys

tests_passed = 0
tests_total = 6

# Test 1: Valid UUID accepted
try:
    action, id = parse_callback_data('ke_approve_550e8400-e29b-41d4-a716-446655440000')
    assert action == 'ke_approve'
    tests_passed += 1
except Exception as e:
    print(f'FAIL: Valid UUID rejected: {e}')

# Test 2: Invalid UUID rejected
try:
    parse_callback_data('ke_approve_not-a-uuid')
    print('FAIL: Invalid UUID accepted')
except CallbackDataError:
    tests_passed += 1

# Test 3: SQL injection attempt rejected
try:
    parse_callback_data('ke_approve_12345; DELETE FROM buyers;')
    print('FAIL: SQL injection accepted')
except CallbackDataError:
    tests_passed += 1

# Test 4: Valid telegram_id accepted
try:
    action, id = parse_callback_data('chat_123456789')
    assert action == 'chat' and id == '123456789'
    tests_passed += 1
except Exception as e:
    print(f'FAIL: Valid telegram_id rejected: {e}')

# Test 5: Non-numeric telegram_id rejected
try:
    parse_callback_data('chat_abc123')
    print('FAIL: Non-numeric telegram_id accepted')
except CallbackDataError:
    tests_passed += 1

# Test 6: Chat SQL injection rejected
try:
    parse_callback_data('chat_12345; DROP TABLE')
    print('FAIL: Chat SQL injection accepted')
except CallbackDataError:
    tests_passed += 1

print(f'{tests_passed}/{tests_total} tests passed')
sys.exit(0 if tests_passed == tests_total else 1)
"
```

## Severity

CRITICAL -> Fixed
