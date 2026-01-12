# Issue #462 - Webhook Error Tracking

## Summary
Added in-memory error tracking for Telegram webhook with monitoring endpoint.

## Changes
- `decision-engine-service/src/routes/telegram.py`:
  - Added `WebhookErrorStats` class for error counting
  - Track errors in `telegram_webhook` (line 2755)
  - Track errors in `process_telegram_update` (line 2650)
  - New endpoint `GET /webhook/telegram/errors`

## Testing
Local test on port 58883:
```bash
# Error trigger
curl -X POST http://localhost:58883/webhook/telegram -d 'invalid json'
# Response: {"ok":true,"error":"Expecting value: line 1 column 1 (char 0)"}

# Check stats
curl http://localhost:58883/webhook/telegram/errors
# Response:
{
    "total_errors": 1,
    "last_error": "Expecting value: line 1 column 1 (char 0)",
    "last_error_time": "2026-01-12T11:43:39.094012",
    "error_types": {
        "JSONDecodeError": 1
    }
}
```

## Notes
- `logger.exception` was already present (traceback logging works)
- In-memory counter resets on service restart
- Returns 200 OK to avoid Telegram retry loops (documented in code)
