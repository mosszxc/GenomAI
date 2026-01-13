# Issue #559: Imports внутри workflow вместо module level

## Что изменено

- Перенесены imports activities из метода `run()` на уровень модуля в `creative_pipeline.py`
- Все imports теперь находятся в блоке `workflow.unsafe.imports_passed_through()` на уровне модуля (строки 21-51)
- Удален дублирующий блок imports внутри метода `run()` (был на строках 107-135)

## Проблема

Imports внутри `async def run()` нарушали правила детерминизма Temporal:
- При replay workflow может получить разные результаты imports
- Это может привести к непредсказуемому поведению в edge cases

## Решение

Canonical паттерн Temporal: все imports должны быть на module level внутри `workflow.unsafe.imports_passed_through()`.

## Test

```bash
grep -n "from temporal.activities" decision-engine-service/temporal/workflows/creative_pipeline.py | head -20 && if grep -A5 "async def run" decision-engine-service/temporal/workflows/creative_pipeline.py | grep -q "imports_passed_through"; then echo "FAIL: imports still in run()"; exit 1; else echo "OK: imports at module level only"; fi
```
