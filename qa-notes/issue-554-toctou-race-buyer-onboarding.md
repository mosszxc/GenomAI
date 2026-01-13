# Issue #554: TOCTOU race в buyer_onboarding wait_condition

## Что изменено

Заменена переменная `_pending_message: Optional[BuyerMessage]` на FIFO очередь `_message_queue: Deque[BuyerMessage]`.

**Проблема:** TOCTOU (Time-of-check to time-of-use) race condition возникала когда:
1. `wait_condition(lambda: self._pending_message is not None)` проверяет наличие сообщения
2. Между проверкой и использованием signal handler мог перезаписать `_pending_message`
3. Workflow обрабатывал не то сообщение которое разблокировало wait

**Решение:** Использование `deque` очереди:
- Signal handler добавляет в конец очереди (`append`)
- Consumer извлекает из начала (`popleft`)
- FIFO гарантирует обработку сообщений в порядке поступления
- Нет race condition — каждое сообщение обрабатывается ровно один раз

## Изменённые файлы

- `temporal/workflows/buyer_onboarding.py`:
  - Добавлен импорт `deque` из `collections`
  - `_pending_message` → `_message_queue: Deque[BuyerMessage]`
  - `_consume_message()` теперь использует `popleft()` вместо прямого доступа
  - `user_message` signal handler использует `append()` вместо присваивания
  - Все `wait_condition` проверки обновлены на `len(self._message_queue) > 0`
  - Snapshot поле `pending_message_exists` → `message_queue_size`

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && uv run python -c "
# Text-based verification
with open('temporal/workflows/buyer_onboarding.py', 'r') as f:
    content = f.read()

# Check for deque import
assert 'from collections import deque' in content, 'deque import not found'

# Check _message_queue initialization
assert '_message_queue: Deque[BuyerMessage] = deque()' in content, '_message_queue init not found'

# Check _pending_message is removed
assert '_pending_message' not in content, '_pending_message should be removed'

# Check wait_condition uses queue
assert 'len(self._message_queue) > 0' in content, 'wait_condition should check queue'

# Check signal handler appends to queue
assert '_message_queue.append(message)' in content, 'signal handler should append to queue'

# Check consume uses popleft
assert '_message_queue.popleft()' in content, 'consume should use popleft'

# Check snapshot field
assert 'message_queue_size' in content, 'snapshot should have message_queue_size'

print('OK: TOCTOU race fix verified')
"
```

## Severity

**HIGH** — исправлена race condition которая могла привести к обработке неправильного сообщения пользователя в onboarding workflow.
