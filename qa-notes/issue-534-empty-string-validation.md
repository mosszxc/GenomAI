# Issue #534: Empty string validation in buyer onboarding workflow

## Что изменено

- Добавлена валидация имени (минимум 2 символа) с циклом повторного запроса
- Добавлена фильтрация пустых строк при парсинге GEO
- Добавлена фильтрация пустых строк при парсинге Verticals
- Добавлено сообщение об ошибке `invalid_name` в MESSAGES

## Файлы

- `decision-engine-service/temporal/workflows/buyer_onboarding.py`

## Исправленные проблемы

1. **Имя баера**: Ранее пустые/короткие имена принимались. Теперь требуется минимум 2 символа.
2. **GEO**: Ранее `"   ".split(",")` возвращало `['']`. Теперь пустые строки фильтруются.
3. **Verticals**: Аналогично GEO.

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-534--empty-string-validation-in-buyer-onboar/decision-engine-service && PYTHONPATH=. python3 -c "from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow, MESSAGES; assert 'invalid_name' in MESSAGES; print('OK: validation code imported successfully')"
```
