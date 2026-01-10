# Testing Rules

## TEST-AFTER-CHANGE (BLOCKING)
**СТОП. Читай это ПЕРЕД закрытием issue или todo.**

### Правило
```
НЕТ ТЕСТА = НЕТ ЗАКРЫТИЯ
```
Validation (структура) ≠ Test (реальный запуск). Validate — это НЕ тест.

### Обязательные тесты по типу изменения
| Изменение | Тест | Критерий успеха |
|-----------|------|-----------------|
| Workflow | WebFetch webhook + `execute_sql` SELECT | HTTP 200 + данные в БД |
| API | `curl` endpoint | HTTP 200 + правильный body |
| Migration | `execute_sql` SELECT | Данные есть + constraints |
| Python | Запустить endpoint | Нет ошибок + output |

**Примечание:** Для Temporal workflows используй `python -m temporal.schedules trigger`.

### Self-Check
Перед словом "готово" спроси себя:
- [ ] Я ЗАПУСТИЛ тест (не validate, а test)?
- [ ] Я ВИДЕЛ результат (execution log, данные в БД)?
- [ ] Если workflow — был WebFetch на webhook + проверка данных в БД?

**Если хоть один ответ "нет" — СТОП, сначала тест.**

## Post-Task Checklist (MANDATORY)
**STOP before saying "done". Check ALL:**
- [ ] **TEST EXECUTED** (WebFetch webhook / curl / execute_sql)
- [ ] **TEST PASSED** (execution success + данные в БД)
- [ ] `qa-notes/{task}.md` created
- [ ] Git commit + push
- [ ] **Lesson learned** recorded (if new pattern discovered)

## Lessons Learned (on issue close)
При закрытии issue — **сначала проверить** `docs/KNOWN_ISSUES.md` → "Lessons Learned":
1. Если похожий урок уже есть → **не дублировать**
2. Если урок новый → записать по шаблону:
```markdown
### Short Title (что пошло не так)

**Context:** Что делали, какой issue
**Mistake:** В чём была ошибка
**Reality:** Что оказалось на самом деле
**Correct Approach:** Как надо было делать
**Rule:** Короткое правило на будущее
```
