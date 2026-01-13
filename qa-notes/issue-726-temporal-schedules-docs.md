# Issue #726: Temporal schedules documentation fix

## Что изменено

- Обновлён `docs/TEMPORAL_WORKFLOWS.md`:
  - Добавлены `metrics-processor` и `learning-loop` в таблицу Schedules
  - Обновлена архитектурная диаграмма — 6 schedules вместо 4
  - Исправлены описания MetricsProcessingWorkflow и LearningLoopWorkflow
  - Добавлено пояснение о двойном запуске (schedule + child workflow)

- Обновлён `CLAUDE.md`:
  - Исправлена таблица Temporal Workflows — убрано "Child of", добавлено "Every 1 hour (+child)"

## Причина

E2E тест выявил несоответствие между кодом и документацией:
- Код `schedules.py` определяет 6 schedules
- Документация указывала только 4 schedules
- На production было только 4 schedules (нужно пересоздать)

`metrics-processor` и `learning-loop` нужны как отдельные schedules для:
1. Catch-up при сбое child chain
2. Recovery scenarios
3. Независимый запуск без полного keitaro poll

## Test

```bash
grep -c "metrics-processor\|learning-loop" /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-726-отсутствуют-temporal-schedules-metrics-p/decision-engine-service/temporal/schedules.py | grep -q "2" && echo "OK: 6 schedules defined"
```
