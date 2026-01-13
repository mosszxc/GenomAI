# Issue #537: Workflow stuck states - timeout deadlock fix

## Что изменено

- Добавлен метод `_consume_message()` для идемпотентной обработки сообщений с дедупликацией
- Добавлено поле `_last_processed_message_id` для отслеживания обработанных сообщений
- Все wait_condition циклы обновлены для использования нового метода

## Проблема

Race condition: если сигнал приходит ПОСЛЕ timeout wait_condition, но ДО проверки `_pending_message is None`:
1. wait_condition возвращает timeout
2. Signal handler обновляет `_pending_message`
3. Workflow обрабатывает старое сообщение или застревает

## Решение

Метод `_consume_message()`:
1. Проверяет наличие сообщения
2. Сравнивает `message_id` с последним обработанным
3. Дубликаты игнорируются, workflow продолжает ждать
4. Новые сообщения обрабатываются и `message_id` сохраняется

## Затронутые файлы

- `decision-engine-service/temporal/workflows/buyer_onboarding.py`

## Test

```bash
python3 -c "
import ast
import inspect

# Parse and verify _consume_message implementation
source = open('temporal/workflows/buyer_onboarding.py').read()
tree = ast.parse(source)

# Find _consume_message method
found = False
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == '_consume_message':
        found = True
        # Check method has deduplication logic
        body_src = ast.unparse(node)
        assert '_last_processed_message_id' in body_src, 'Missing deduplication field'
        assert 'message_id' in body_src, 'Missing message_id check'
        print('_consume_message method has deduplication logic')
        break

assert found, '_consume_message method not found'

# Verify all wait_condition loops use _consume_message
assert source.count('_consume_message()') >= 5, 'Not all loops updated'
print(f'Found {source.count(chr(95) + \"consume_message()\")} calls to _consume_message')

# Verify _last_processed_message_id initialized in __init__
assert '_last_processed_message_id: Optional[int] = None' in source, 'Missing field init'
print('Field _last_processed_message_id properly initialized')

print('All structural tests passed')
"
```
