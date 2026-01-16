# Issue #746: HTTP 401 при валидации Keitaro в онбоардинге

## Проблема

Cockpit frontend передавал Supabase JWT токен, но `verify_jwt_token` ожидал только кастомный формат `buyer_id:timestamp:signature`.

## Root Cause

Функция `verify_jwt_token` в `onboarding.py` не поддерживала Supabase JWT формат — только кастомный токен от `/api/auth/telegram`.

## Решение

1. Добавлен PyJWT в `requirements.txt`
2. Модифицирована функция `verify_jwt_token`:
   - Определяет формат токена (JWT vs кастомный)
   - Для JWT: декодирует payload и извлекает `sub` (buyer_id)
   - Для кастомного: проверяет HMAC signature
3. Оба формата теперь поддерживаются

## Изменённые файлы

- `decision-engine-service/requirements.txt` — добавлен PyJWT
- `decision-engine-service/src/routes/onboarding.py` — поддержка Supabase JWT
- `tests/unit/test_onboarding_auth.py` — тесты для обоих форматов

## Test

```bash
PYTHONPATH=decision-engine-service python3 -m pytest tests/unit/test_onboarding_auth.py -v && echo "OK: tests passed"
```
