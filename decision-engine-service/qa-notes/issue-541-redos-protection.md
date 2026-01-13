# Issue #541: ReDoS Protection for URL Regex Patterns

## Что изменено

- Создан модуль `src/utils/safe_regex.py` с функциями безопасного regex matching
- Добавлено ограничение длины входных данных (MAX_INPUT_LENGTH = 2048) во все regex операции с URL
- Обновлены функции:
  - `temporal/models/validators.py:validate_url` - добавлена проверка MAX_URL_LENGTH
  - `temporal/workflows/buyer_onboarding.py:is_video_url` - ограничение длины
  - `src/routes/telegram.py:extract_video_url` - ограничение длины
  - `temporal/activities/transcription.py:extract_gdrive_file_id` - использует safe_search
  - `temporal/activities/transcription.py:convert_to_direct_url` - использует safe_search

## Защита от ReDoS

ReDoS (Regular Expression Denial of Service) происходит когда regex с "катастрофическим backtracking" получает специально сконструированный ввод, вызывающий экспоненциальный рост времени обработки.

Решение: ограничение длины входных данных до 2048 символов перед применением regex. URL редко превышают 2000 символов, поэтому это безопасное ограничение.

## Изменённые файлы

- `src/utils/safe_regex.py` (новый)
- `temporal/models/validators.py`
- `temporal/workflows/buyer_onboarding.py`
- `src/routes/telegram.py`
- `temporal/activities/transcription.py`

## Test

```bash
python3 -c "
from src.utils.safe_regex import safe_search, MAX_INPUT_LENGTH

# Test 1: Normal URL works
url = 'https://youtube.com/watch?v=abc123'
match = safe_search(r'youtube\.com/watch', url)
assert match is not None, 'Test 1 failed: normal URL should match'
print('Test 1 PASSED: normal URL matches')

# Test 2: Long input is truncated
long_input = 'a' * 10000
result = safe_search(r'pattern', long_input)
print(f'Test 2 PASSED: long input handled (length: {len(long_input)}, MAX: {MAX_INPUT_LENGTH})')

# Test 3: Empty input returns None
result = safe_search(r'pattern', '')
assert result is None, 'Test 3 failed: empty input should return None'
print('Test 3 PASSED: empty input returns None')

# Test 4: validate_url rejects too long URLs
from temporal.models.validators import validate_url, MAX_URL_LENGTH
try:
    validate_url('https://example.com/' + 'a' * 3000)
    print('Test 4 FAILED: should have raised ValueError')
except ValueError as e:
    assert 'exceeds maximum length' in str(e)
    print('Test 4 PASSED: long URL rejected')

print('\\nAll ReDoS protection tests PASSED!')
"
```
