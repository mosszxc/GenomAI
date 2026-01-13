# Issue #535: Callback query input injection vulnerability

## Что изменено

- Усилена валидация в функции `parse_callback_data()`:
  - `extraction_id` (ke_approve/ke_reject/ke_skip) теперь валидируется как UUID
  - `buyer_telegram_id` (chat_) теперь валидируется как числовое значение
- Добавлено логирование попыток инъекции через `CallbackDataError`

## Файлы

- `decision-engine-service/src/routes/telegram.py:117-169`

## Защита от атак

**До (только regex):**
```python
CALLBACK_DATA_PATTERN = re.compile(r"^[a-z_]+_[a-zA-Z0-9\-]+$")
# Пропускает: "ke_approve_not-a-uuid", "chat_abc123"
```

**После (type-specific validation):**
```python
if action in ("ke_approve", "ke_reject", "ke_skip"):
    uuid_module.UUID(identifier)  # Raises ValueError if invalid
elif action == "chat":
    if not identifier.isdigit():
        raise CallbackDataError("Invalid telegram_id")
```

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-535-callback-injection/decision-engine-service && python3 -c "
import sys
sys.path.insert(0, 'src')
from routes.telegram import parse_callback_data, CallbackDataError

# Test 1: Valid UUID for ke_approve
action, id = parse_callback_data('ke_approve_550e8400-e29b-41d4-a716-446655440000')
assert action == 'ke_approve'
print('Valid UUID: OK')

# Test 2: Invalid UUID rejected
try:
    parse_callback_data('ke_approve_not-a-uuid')
    print('FAIL: invalid UUID passed')
    exit(1)
except CallbackDataError:
    print('Invalid UUID rejected: OK')

# Test 3: SQL injection rejected
try:
    parse_callback_data('ke_approve_12345; DELETE')
    print('FAIL: injection passed')
    exit(1)
except CallbackDataError:
    print('SQL injection rejected: OK')

# Test 4: Valid telegram_id
action, id = parse_callback_data('chat_123456789')
assert action == 'chat' and id == '123456789'
print('Valid telegram_id: OK')

# Test 5: Non-numeric telegram_id rejected
try:
    parse_callback_data('chat_abc123')
    print('FAIL: non-numeric passed')
    exit(1)
except CallbackDataError:
    print('Non-numeric telegram_id rejected: OK')

print('All security checks passed')
"
```
