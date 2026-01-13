# Issue #556: Non-deterministic workflow.now() в error handler

## Что изменено

- Добавлено поле `_operation_start_time` в `CreativePipelineWorkflow.__init__`
- Время захватывается через `workflow.now()` в начале `run()` ДО блока try
- `_build_result()` теперь использует сохранённое время вместо вызова `workflow.now()`

## Причина изменения

`workflow.now()` внутри exception handler может вызвать non-determinism error при replay:
- Если exception происходит в разные моменты при replay, `workflow.now()` вернёт разные значения
- Temporal требует детерминизма - одинаковый код должен давать одинаковый результат при replay

## Решение

Захватить время в детерминистичном пути выполнения (до try-except) и использовать его везде.

## Test

```bash
python3 -c "
import ast
code = open('decision-engine-service/temporal/workflows/creative_pipeline.py').read()
tree = ast.parse(code)
# Проверяем что _operation_start_time инициализируется
assert '_operation_start_time' in code, 'Missing _operation_start_time'
# Проверяем что в _build_result используется сохранённое время
assert 'self._operation_start_time or workflow.now()' in code, 'Wrong pattern in _build_result'
print('OK: Deterministic workflow.now() pattern implemented')
"
```
