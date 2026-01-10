# Issue #280: Telegram bot returns "Session timed out" on /start command

## Problem
При отправке `/start` в Telegram бот возвращал "Session timed out due to inactivity" через 2-3 секунды вместо ожидания 60 минут на ввод пользователя.

## Root Cause (ACTUAL)
`workflow.wait_condition()` возвращает `None` когда signal приходит во время ожидания:

```
11:29:55 - Waiting for user input with timeout: 3600.0 seconds
11:29:55 - _pending_message before wait: None
11:29:57 - wait_condition returned: None  <-- НЕ True!
11:29:57 - _pending_message after wait: BuyerMessage(text='moss', ...)
11:29:57 - wait_condition timed out unexpectedly!
```

Проблема в коде:
```python
if not await workflow.wait_condition(...):  # None is falsy!
    return await self._handle_timeout()
```

`None` — falsy value в Python, поэтому `if not None` = `True` → срабатывал timeout хотя сообщение УЖЕ ПОЛУЧЕНО!

## Fix
Проверяем фактическое состояние `_pending_message` вместо return value:

```python
await workflow.wait_condition(
    lambda: self._pending_message is not None,
    timeout=step_timeout,
)
if self._pending_message is None:  # Check actual state
    return await self._handle_timeout()
```

## Files Changed
- `decision-engine-service/temporal/workflows/buyer_onboarding.py` — исправлены все 4 места с wait_condition
- `decision-engine-service/src/routes/telegram.py` — переписан `handle_start_command` (дополнительное улучшение)

## Testing
1. `/start` → welcome message ✓
2. Ввод имени "moss" → ask for GEOs ✓
3. Полный onboarding flow работает ✓

## Lesson Learned
**Temporal SDK Python: wait_condition может вернуть None**

При использовании `wait_condition` с signals:
- НЕ полагаться на return value (`if not result:`)
- ВСЕГДА проверять фактическое состояние переменной (`if var is None:`)

## Related
- Issue #260: Buyer Stats Command (обнаружено при тестировании)
