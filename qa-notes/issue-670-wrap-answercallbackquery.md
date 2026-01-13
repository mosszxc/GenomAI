# Issue #670: wrap answerCallbackQuery in try/except

## Что изменено
- Обернули `answerCallbackQuery` вызов в try/except в `telegram.py:2479-2487`
- При ошибке (timeout, network error, rate limit) логируем warning и продолжаем обработку callback
- Юзер больше не будет видеть "Loading..." вечно при сетевых проблемах

## Test
```bash
cd decision-engine-service && python -c "
import ast
with open('src/routes/telegram.py') as f:
    content = f.read()
# Check that answerCallbackQuery is inside try block
if 'try:' in content and 'answerCallbackQuery' in content:
    # Find the try block containing answerCallbackQuery
    idx = content.find('answerCallbackQuery')
    before = content[max(0, idx-200):idx]
    if 'try:' in before and 'except Exception as e:' in content[idx:idx+300]:
        print('OK: answerCallbackQuery wrapped in try/except')
    else:
        print('FAIL: try/except not properly structured')
        exit(1)
else:
    print('FAIL: answerCallbackQuery or try not found')
    exit(1)
"
```
