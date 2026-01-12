# QA Notes: Issue #466 - Staleness Detector Error Logging

## Problem
Silent fallbacks in `staleness_detector.py` were hiding DB errors:
- 5 `except Exception` blocks returned neutral values (0.5, 0.0) without logging
- System appeared healthy when DB was unavailable
- staleness_score computed incorrectly with fallback values

## Solution
1. Added `logging` import and `logger` instance
2. Added `error_sources: list` field to `StalenessMetrics` dataclass
3. Each except block now:
   - Logs ERROR with exception details, avatar_id, geo
   - Appends metric name to error_sources
4. Warning logged when any metrics use fallback values
5. `check_staleness_and_act` returns `has_db_errors` and `error_sources` in result

## Files Changed
- `decision-engine-service/src/services/staleness_detector.py`
- `decision-engine-service/tests/unit/test_staleness_detector.py` (new)

## Tests
```
pytest tests/unit/test_staleness_detector.py -v
6 passed in 0.07s

pytest tests/unit/ -v
163 passed in 0.58s
```

## Test Coverage
- `test_error_sources_tracked_on_db_failure` - verifies errors tracked
- `test_no_errors_when_db_succeeds` - verifies clean state
- `test_errors_are_logged` - verifies ERROR level logging
- `test_all_errors_fallback_warning_logged` - verifies WARNING summary
- `test_staleness_metrics_dataclass_has_error_sources` - verifies field
- `test_error_sources_default_empty` - verifies default

## API Response Example
```json
{
  "metrics": {...},
  "is_stale": false,
  "has_db_errors": true,
  "error_sources": ["diversity_score", "win_rate_trend"]
}
```

Consumers can now check `has_db_errors` to know if results are reliable.
