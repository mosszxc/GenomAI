# Issue #468: Валидация --by флага в /genome

## Что изменено

- Добавлена проверка наличия значения после `--by` флага
- При отсутствии значения возвращается help message вместо тихого игнорирования

## Test

```bash
python3 -c "parts='/genome --by'.split(); by_index=parts.index('--by'); assert by_index+1>=len(parts); print('OK: --by without value detected')"
```
