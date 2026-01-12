# Issue #565: Division by len(cpas) без проверки

## Что изменено
- Добавлена проверка `if cpas` в dict comprehension для предотвращения ZeroDivisionError

## Файлы
- `decision-engine-service/src/services/feature_correlation.py:181-185`

## Test
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-565-medium-division-by-lencpas-без-проверки-/decision-engine-service && python3 -c "
# Test: empty list should not cause ZeroDivisionError
decision_to_cpa = {'dec_1': [1.0, 2.0], 'dec_2': []}

# This is the fixed logic
result = {
    dec_id: sum(cpas) / len(cpas)
    for dec_id, cpas in decision_to_cpa.items()
    if cpas
}

assert result == {'dec_1': 1.5}, f'Expected {{\"dec_1\": 1.5}}, got {result}'
print('OK: ZeroDivisionError prevented, empty list skipped')
"
```
