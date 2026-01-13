# Issue #548: Silent fallback в keitaro_polling workflow

## Что изменено

- `keitaro_polling.py:236`: Добавлен `is_degraded = True` при ошибке `get_batch_metrics`
- `keitaro_polling.py:220`: Добавлен `circuit_state` в return при пустых trackers
- `keitaro_polling.py:370-381`: Добавлено warning логирование для degraded mode

## Проблема

При ошибках API в `get_batch_metrics` workflow продолжал работу с `is_degraded=False`,
что скрывало реальные проблемы от мониторинга. Event emission и финальный результат
показывали успешное выполнение, хотя данные были неполными.

## Решение

1. Явная установка `is_degraded=True` во всех error paths
2. Консистентное распространение `circuit_state` во всех return statements
3. Warning-уровень логирования для degraded completions

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-548-critical-молчаливые-fallback-в-keitaropo/decision-engine-service && python -c "from temporal.workflows.keitaro_polling import KeitaroPollerWorkflow; print('OK: workflow imports')"
```
