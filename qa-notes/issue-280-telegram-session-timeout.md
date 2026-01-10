# Issue #280: Telegram bot returns "Session timed out" on /start command

## Problem
При отправке `/start` в Telegram бот возвращал "Session timed out due to inactivity" вместо регистрации нового buyer.

## Root Cause
Race condition в `handle_start_command`:
1. `check_active_onboarding` делал query на workflow и получал состояние AWAITING_NAME
2. Workflow ID возвращался как "активный"
3. В промежутке между query и ответом "already have active registration", workflow мог таймаутиться
4. Workflow отправлял "Session timed out"
5. Пользователь получал это сообщение вместо ожидаемого ответа

## Fix
Заменили логику с query-based проверки на Temporal-native подход:
- Используем `id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE` — позволяет перезапустить workflow после timeout/completion
- Используем `id_conflict_policy=WorkflowIDConflictPolicy.FAIL` — бросает `WorkflowAlreadyStartedError` если workflow ещё running
- Ловим `WorkflowAlreadyStartedError` и отправляем "already have active registration"

Это устраняет race condition потому что Temporal гарантирует atomicity при start_workflow.

## Files Changed
- `decision-engine-service/src/routes/telegram.py` — переписан `handle_start_command`

## Testing
После deploy нужно:
1. Отправить `/start` новому пользователю → должен получить welcome message
2. Отправить `/start` повторно пока onboarding активен → должен получить "already have active registration"
3. Подождать timeout и отправить `/start` снова → должен получить новый welcome message

## Related
- Issue #260: Buyer Stats Command (обнаружено при тестировании)
