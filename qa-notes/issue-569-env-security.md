# Issue #569: [SECURITY] .env файлы с production credentials

## Что изменено
- Проверено: `.env` файлы НЕ были в git (уже в .gitignore)
- Добавлен `.env.example` в корень проекта
- Добавлен `decision-engine-service/.env.example`

## Анализ
Issue был создан автоматическим аудитом, который обнаружил .env файлы локально,
но не проверил, что они не отслеживаются git.

Проверки:
- `git ls-files | grep '\.env$'` - пусто (не в git)
- `git log --all -- '*.env'` - пусто (никогда не были)
- `.gitignore` содержит `.env` с строки 38

## Test
```bash
# Проверка: .env не в git
test -z "$(git ls-files | grep '\.env$')" && echo "OK: .env not tracked"
```
