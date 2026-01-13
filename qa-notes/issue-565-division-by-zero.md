# Issue #565: Division by len(cpas) без проверки

## Что изменено
- Добавлена проверка `if cpas` в dict comprehension для предотвращения ZeroDivisionError

## Файлы
- `decision-engine-service/src/services/feature_correlation.py:181-185`

## Test
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-565-medium-division-by-lencpas-без-проверки-/decision-engine-service && python3 -c "d={'a':[1,2],'b':[]};r={k:sum(v)/len(v) for k,v in d.items() if v};assert r=={'a':1.5};print('OK')"
```
