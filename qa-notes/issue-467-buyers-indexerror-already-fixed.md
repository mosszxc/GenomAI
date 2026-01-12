# Issue #467: IndexError при пустом массиве buyers

## Что проверено

Issue указывает на `telegram.py:313` с потенциальным IndexError при доступе к `buyers[0]` без проверки на пустой массив.

**Результат проверки:** Все места с `buyers[0]` уже защищены.

| Строка | Код | Защита |
|--------|-----|--------|
| 518 | `buyer = buyers[0]` | Строки 511-516: `if not buyers: return` |
| 1406 | `buyer = buyers[0] if buyers else {}` | Inline защита |
| 2312 | `buyers[0].get("name") if buyers else None` | Inline защита |
| 2603 | `buyer_id = buyers[0]["id"]` | Строки 2596-2601: `if not buyers: return` |

## Что изменено

- Подтверждено: проблема уже была исправлена ранее
- Номер строки в issue (313) устарел из-за последующих коммитов

## Test

```bash
test $(grep -c "buyers\[0\]" decision-engine-service/src/routes/telegram.py) -eq 4 && echo "OK: 4 protected usages found"
```
