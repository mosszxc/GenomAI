# Issue #550: HTTP error handling in Keitaro activities

## Что изменено
- Добавлена функция `_handle_http_response()` для обработки HTTP ошибок
- Временные ошибки (502, 503, 504, 429) → `ApplicationError(non_retryable=False)` → Temporal retry
- Постоянные ошибки (4xx, 5xx) → `ApplicationError(non_retryable=True)` → no retry
- Заменены все 5 вызовов `response.raise_for_status()` на `_handle_http_response()`
- Добавлено логирование деталей ошибок

## Файлы
- `decision-engine-service/temporal/activities/keitaro.py`

## Test
```bash
cd decision-engine-service && python3 -c "
from unittest.mock import Mock
import httpx
from temporal.activities.keitaro import _handle_http_response, _TEMPORARY_ERROR_CODES
from temporalio.exceptions import ApplicationError

# Test 1: Success response - no exception
mock_ok = Mock(spec=httpx.Response)
mock_ok.is_success = True
_handle_http_response(mock_ok)
print('OK: Success response handled')

# Test 2: Temporary error (503) - retryable
mock_503 = Mock(spec=httpx.Response)
mock_503.is_success = False
mock_503.status_code = 503
mock_503.text = 'Service Unavailable'
try:
    _handle_http_response(mock_503)
    print('FAIL: Should have raised')
    exit(1)
except ApplicationError as e:
    if e.non_retryable:
        print('FAIL: 503 should be retryable')
        exit(1)
    print('OK: 503 is retryable')

# Test 3: Permanent error (401) - non-retryable
mock_401 = Mock(spec=httpx.Response)
mock_401.is_success = False
mock_401.status_code = 401
mock_401.text = 'Unauthorized'
try:
    _handle_http_response(mock_401)
    print('FAIL: Should have raised')
    exit(1)
except ApplicationError as e:
    if not e.non_retryable:
        print('FAIL: 401 should be non-retryable')
        exit(1)
    print('OK: 401 is non-retryable')

print('ALL TESTS PASSED')
"
```
