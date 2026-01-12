# QA Notes: Issue #469 - datetime.fromisoformat try-catch

## Summary
Added try-catch wrapper around `datetime.fromisoformat()` in keitaro activity to prevent workflow crashes on invalid date format.

## Changes
- File: `decision-engine-service/temporal/activities/keitaro.py`
- Added import: `from temporalio.exceptions import ApplicationError`
- Wrapped `datetime.fromisoformat(input.date_from)` in try-except
- On ValueError: raises `ApplicationError` with `non_retryable=True`

## Why non_retryable=True
Invalid date format is a data error, not a transient failure. Retrying won't fix bad input - it would just waste resources. The error should surface immediately so the caller can fix the input.

## Testing
- Pre-commit hooks passed (lint, format, critical tests)
- Pre-push hooks passed (all unit tests)
- CI checks passed (Contract Validation, Integration Tests, Unit Tests)
- Production deploy: live
- Health check: OK

## Risk Assessment
Low risk - defensive change that only adds error handling without changing happy path behavior.
