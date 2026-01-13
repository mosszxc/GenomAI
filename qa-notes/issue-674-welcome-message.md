# Issue #674: Improve Welcome Message

## Что изменено

- Улучшено welcome_back сообщение в `BuyerOnboardingWorkflow`
- Заменено сухое английское "Welcome back" на информативное русское сообщение
- Добавлено объяснение как работает система (3 шага)
- Добавлены команды `/stats` и `/help`
- Добавлен call-to-action "Отправь первый креатив!"

## Файлы

- `decision-engine-service/temporal/workflows/buyer_onboarding.py`

## Test

```bash
cd decision-engine-service && python -c "from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow; print('OK: workflow imports')"
```
