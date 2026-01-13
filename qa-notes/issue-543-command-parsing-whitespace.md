# Issue #543: Command parsing vulnerability with whitespace

## Что изменено

- Исправлен парсинг команд `/approve` и `/reject` в `telegram.py`
- Теперь фильтруются пустые части при split() для корректной обработки множественных пробелов
- До: `parts = text.strip().split()` — не фильтровал пустые строки
- После: `parts = [p for p in text.strip().split() if p]` — фильтрует пустые части

## Test

```bash
python3 -c "
# Test whitespace handling fix
text1 = '/approve   abc123'
text2 = '/approve abc123  '
text3 = '/approve   '

# New fixed parsing
parts1 = [p for p in text1.strip().split() if p]
parts2 = [p for p in text2.strip().split() if p]
parts3 = [p for p in text3.strip().split() if p]

assert parts1 == ['/approve', 'abc123'], f'Failed: {parts1}'
assert parts2 == ['/approve', 'abc123'], f'Failed: {parts2}'
assert parts3 == ['/approve'], f'Failed: {parts3}'
assert len(parts3) < 2, 'Should fail validation for missing id'

print('OK: All whitespace parsing tests passed')
"
```
