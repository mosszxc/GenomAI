# Issue #552: Race condition в metrics_processing

## Что изменено

- Убрано присваивание результата `start_child_workflow()` переменной `learning_triggered`
- `learning_triggered = True` теперь устанавливается только после успешного запуска child workflow
- Если `start_child_workflow()` выбросит исключение, `learning_triggered` останется `False`

## Проблема

```python
# ДО: Результат перезаписывался
learning_triggered = await workflow.start_child_workflow(...)  # handle
learning_triggered = True  # перезаписывает handle!
```

```python
# ПОСЛЕ: Корректная логика
await workflow.start_child_workflow(...)  # fire-and-forget
learning_triggered = True  # только если успешно запущен
```

## Test

```bash
cd decision-engine-service && python -c "
import ast
with open('temporal/workflows/metrics_processing.py') as f:
    tree = ast.parse(f.read())

# Find the workflow class
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'learning_triggered':
                if isinstance(node.value, ast.Await):
                    print('FAIL: learning_triggered assigned from await')
                    exit(1)

print('OK: No race condition found')
"
```
