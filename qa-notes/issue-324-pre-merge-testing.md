# QA Notes: Issue #324 - Pre-merge local testing workflow

## Summary
Добавлен workflow локального тестирования Python-кода перед merge и deploy.

## Changes Made

### 1. `.pre-commit-config.yaml`
- Добавлен `default_install_hook_types: [pre-commit, pre-push]`
- Убран `|| true` — тесты теперь блокируют commit/push
- Добавлен `critical-tests` hook на `pre-commit` стадии (hashing parity)
- Переименован `fast-tests` → `all-unit-tests` на `pre-push`

### 2. `Makefile` (новый)
- `make test` — critical tests (~15s)
- `make test-unit` — all unit tests (~45s)
- `make e2e-quick` — health check на сервере
- `make setup-hooks` — установка git hooks

### 3. `docs/E2E_SERVER_CHECKLIST.md` (новый)
- Пошаговый чеклист E2E тестирования на сервере
- SQL queries для проверки pipeline
- Troubleshooting table

### 4. `CLAUDE.md`
- Добавлена секция "Pre-Merge Testing"

## Verification

```bash
# Makefile работает
make help  # OK

# e2e-quick работает
make e2e-quick  # Health check: 200
```

## Notes
- pytest не установлен в venv на момент тестирования
- После `make install` тесты будут работать
- Pre-commit hooks требуют `make setup-hooks` для активации

## Testing Workflow
```
1. git commit → pre-commit (lint + hashing tests)
2. git push → pre-push (all unit tests)
3. deploy → make e2e-quick / make e2e
```

## Additional Changes (2026-01-11)

### 5. `scripts/task-done.sh`
- Добавлен блок PRE-MERGE CHECKS с `make ci` перед push
- Блокирует PR при failed checks

### 6. `.github/workflows/ci.yml` (новый)
- CI workflow: lint → format-check → test → contracts
- Запускается на push в main и PR

### 7. Makefile / pre-commit-config.yaml
- Исправлен путь к ruff: `ruff` → `python3 -m ruff`
- Добавлена проверка наличия pytest

### Verification
```bash
make ci  # All checks passed
```
