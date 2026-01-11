# QA Notes: Issue #380 - ModularHypothesisWorkflow

## Summary
Создан Temporal workflow для оркестрации модульной генерации гипотез.

## Changes
- `temporal/workflows/modular_hypothesis.py` — новый workflow
- `temporal/workflows/__init__.py` — экспорт
- `temporal/worker.py` — регистрация в creative-pipeline queue
- `docs/TEMPORAL_WORKFLOWS.md` — документация

## Workflow Logic
1. `check_modular_readiness` — проверка достаточности модулей
2. `select_module_combinations` — выбор комбинаций (hook→promise→proof)
3. `synthesize_hypothesis_text` — LLM синтез для каждой комбинации
4. `save_modular_hypothesis` — сохранение с review_status=pending_review

## Requirements for Activation
- hooks >= 3 (status=active)
- promises >= 3 (status=active)
- proofs >= 2 (status=active)
- explored modules >= 2 (sample_size >= 5)

## Test Status

### Pre-deployment
- [x] Import OK: `from temporal.workflows.modular_hypothesis import ModularHypothesisWorkflow`
- [x] Worker import OK: `from temporal.worker import run_all_workers`
- [x] Unit tests passed (35/35)
- [x] Pre-commit hooks passed (lint, format, critical tests)
- [x] Pre-push hooks passed (all unit tests)
- [x] CI checks passed (Lint, Unit Tests, Contract Validation, Integration Tests)

### Post-deployment
- [x] Deploy status: `live` (dep-d5hsot1enlqs73eeifs0)
- [x] Health check: `{"status":"ok"}`
- [x] Service running: uvicorn on port 10000

### Production Test
**Status:** PARTIAL — workflow корректно зарегистрирован, но E2E невозможен

**Причина:** Недостаточно модулей в БД для генерации
```
module_type | status   | count | required
------------|----------|-------|----------
hook        | emerging | 1     | 3 (active)
promise     | emerging | 1     | 3 (active)
proof       | emerging | 1     | 2 (active)
```

**Expected behavior:** Workflow вернёт `success=False, error="Not ready: Insufficient modules"`

## Post-Task Loop
- [x] qa-notes written
- [x] docs/TEMPORAL_WORKFLOWS.md updated
- [x] PR #415 merged
- [x] Issue #380 closed

## Notes
- Workflow корректно обработает "not ready" сценарий
- Полный E2E тест возможен после накопления модулей через LearningLoop
- Activities уже реализованы в #379, workflow оркестрирует их
- Temporal worker логи не видны в Render (отдельный процесс)

## Tested By
Claude Opus 4.5 @ 2026-01-11
