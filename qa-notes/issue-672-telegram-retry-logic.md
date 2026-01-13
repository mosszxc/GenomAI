# Issue #672: Add retry logic to send_hypothesis_to_telegram

## Summary
Added retry logic to `send_hypothesis_to_telegram` activity to handle transient Telegram API failures.

## Changes
- **File:** `decision-engine-service/temporal/activities/telegram.py`
- Added retry configuration constants: `MAX_RETRIES=3`, `BASE_DELAY=1.0s`, `MAX_DELAY=10.0s`
- Added `_should_retry()` function: retries on 429 (rate limit) and 5xx (server errors)
- Added `_get_retry_delay()` function: exponential backoff with Retry-After header support
- Updated `send_hypothesis_to_telegram` with retry loop:
  - Max 3 attempts with exponential backoff (1s, 2s, 4s)
  - Respects Telegram's Retry-After header for rate limits
  - Handles `httpx.TimeoutException` and `httpx.HTTPError`
  - Raises `TELEGRAM_RETRY_EXHAUSTED` error when all retries fail

## Test

```bash
cd decision-engine-service && python3 -c "
from temporal.activities.telegram import (
    _should_retry, _get_retry_delay, MAX_RETRIES, BASE_DELAY, MAX_DELAY
)

# Test _should_retry
assert _should_retry(429) == True, 'Should retry on 429'
assert _should_retry(500) == True, 'Should retry on 500'
assert _should_retry(503) == True, 'Should retry on 503'
assert _should_retry(400) == False, 'Should not retry on 400'
assert _should_retry(404) == False, 'Should not retry on 404'

# Test _get_retry_delay
assert _get_retry_delay(0) == 1.0, 'First retry delay should be 1s'
assert _get_retry_delay(1) == 2.0, 'Second retry delay should be 2s'
assert _get_retry_delay(2) == 4.0, 'Third retry delay should be 4s'
assert _get_retry_delay(0, retry_after=5) == 5.0, 'Should respect Retry-After'
assert _get_retry_delay(0, retry_after=100) == MAX_DELAY, 'Should cap at MAX_DELAY'

# Test constants
assert MAX_RETRIES == 3
assert BASE_DELAY == 1.0
assert MAX_DELAY == 10.0

print('All tests passed!')
"
```
