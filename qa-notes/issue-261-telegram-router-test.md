# Issue #261: Test Telegram Router Process

**Date**: 2026-01-10
**Type**: Validation Test
**Process**: telegram-router

## Summary

Validated Telegram Router implementation in FastAPI (`decision-engine-service/src/routes/telegram.py`).

## Test Results

### Commands Tested

| Command | Expected Handler | Actual | Status |
|---------|-----------------|--------|--------|
| /start | BuyerOnboarding | `handle_start_command` → `BuyerOnboardingWorkflow` | PASS |
| /stats | StatsCommand | `handle_stats_command` → Direct Supabase query | PASS |
| /help | HelpCommand | `handle_help_command` → Static message | PASS |
| /zaliv | ZalivSession | **NOT IMPLEMENTED** | FAIL |
| video | CreativeRegistration | `handle_video_url` → `CreativeRegistrationWorkflow` | PASS (URL only) |
| callback | CallbackHandler | **NOT IMPLEMENTED** | FAIL |

### Webhook Status

```json
{
  "status": "configured",
  "url": "https://genomai.onrender.com/webhook/telegram",
  "pending_update_count": 0,
  "last_error_date": null,
  "last_error_message": null
}
```

**Verdict**: Webhook correctly configured and operational.

### Logging to buyer_interactions

| Handler | Incoming Log | Outgoing Log | Status |
|---------|-------------|--------------|--------|
| /start | NO | NO | PARTIAL |
| /stats | YES | YES | PASS |
| /help | NO | NO | FAIL |
| video URL | NO | NO | FAIL |

**Issue**: Only `/stats` command logs to `buyer_interactions`. Other commands don't log interactions.

## Issues Found

### 1. `/zaliv` Command Not Implemented

- **Severity**: Medium
- **Location**: `telegram.py`
- **Expected**: Starts ZalivSession for batch upload
- **Actual**: Returns "Unknown command" error
- **Impact**: Users cannot use batch upload session

### 2. Callback Query Handler Missing

- **Severity**: Medium
- **Location**: `telegram.py:parse_update()`
- **Expected**: Handle `callback_query` from inline buttons
- **Actual**: Only `message` is parsed, callbacks ignored
- **Impact**: Inline keyboard buttons won't work

### 3. Incomplete Interaction Logging

- **Severity**: Low
- **Location**: `telegram.py`
- **Expected**: All interactions logged to `buyer_interactions`
- **Actual**: Only `/stats` logs both directions
- **Impact**: Incomplete audit trail

### 4. Direct Video Upload Not Supported

- **Severity**: Low (by design)
- **Location**: `telegram.py:process_telegram_update()`
- **Expected**: Process uploaded video files
- **Actual**: Returns message asking for URL instead
- **Impact**: Users must provide URLs, not upload directly

## Architecture Notes

- **Router**: FastAPI endpoint `/webhook/telegram`
- **Onboarding**: Temporal workflow `BuyerOnboardingWorkflow`
- **Creative Registration**: Temporal workflow `CreativeRegistrationWorkflow`
- **State Machine**: 5 states (AWAITING_NAME → AWAITING_GEO → AWAITING_VERTICAL → AWAITING_KEITARO → LOADING_HISTORY → COMPLETED)

## Recommendations

1. **Add `/zaliv` handler** - Create `handle_zaliv_command()` for batch sessions
2. **Add callback_query support** - Extend `parse_update()` to handle callbacks
3. **Extend logging** - Add `log_buyer_interaction()` calls to all handlers
4. **Consider video upload** - Evaluate if direct upload should be supported

## Files Reviewed

- `decision-engine-service/src/routes/telegram.py` (main router)
- `decision-engine-service/temporal/workflows/buyer_onboarding.py`
- `decision-engine-service/temporal/workflows/historical_import.py`

## Conclusion

Telegram Router is **partially functional**:
- Core commands (/start, /stats, /help) work correctly
- Video URL registration works
- Webhook is configured and operational
- Missing: /zaliv, callback queries, complete logging

**Recommendation**: Create follow-up issues for missing functionality.
