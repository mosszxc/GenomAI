# Issue #547: Двойной response.json() — потеря данных и неэффективность

## Что изменено

Исправлен паттерн двойного вызова `response.json()` в 5 файлах (8 мест):

| Файл | Строки |
|------|--------|
| `learning_loop.py` | 389 |
| `exploration.py` | 247, 286 |
| `recommendation.py` | 490, 524 |
| `premise_learning.py` | 244, 263 |
| `staleness_detector.py` | 579 (бонус) |

**Было:**
```python
return response.json()[0] if response.json() else {}
```

**Стало:**
```python
data = response.json()
return data[0] if data else {}
```

## Почему это важно

1. `response.json()` потребляет тело ответа (stream)
2. Повторный вызов может вернуть пустой результат или ошибку
3. Неэффективность — двойной парсинг JSON

## Test

```bash
grep -r "response\.json().*response\.json()" decision-engine-service/ && exit 1 || echo "OK: no double response.json() found"
```
