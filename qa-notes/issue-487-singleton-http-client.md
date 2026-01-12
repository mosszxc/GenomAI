# Issue #487: Singleton HTTP Client

## Что изменено

- Создан `src/core/http_client.py` с singleton httpx.AsyncClient
- Мигрированы 48 файлов для использования `get_http_client()` вместо `async with httpx.AsyncClient()`
- Connection pooling: max_connections=100, max_keepalive=20
- Кастомные timeout сохранены через передачу в запрос (timeout=X в client.get/post)
- Обновлены 2 тестовых файла для мока нового паттерна

## Затронутые файлы

### Новые
- `src/core/__init__.py`
- `src/core/http_client.py`

### Мигрированные (48 файлов)
- temporal/activities/*.py (17 файлов)
- src/services/*.py (21 файл)
- src/routes/*.py (4 файла)
- scripts/test_*.py (2 файла)
- src/services/features/component_pair_winrate.py

### Тесты
- tests/unit/test_creative_failed_status.py
- tests/unit/test_learning_idempotency.py

## Test

```bash
cd decision-engine-service && python3 -c "from src.core.http_client import get_http_client; c1 = get_http_client(); c2 = get_http_client(); print('OK: singleton' if c1 is c2 else 'FAIL')"
```

## Ожидаемый результат

```
OK: singleton
```
