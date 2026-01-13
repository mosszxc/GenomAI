# Issue #694: Nondeterminism error blocks webhook processing

## What changed
- Added graceful handling of Nondeterminism errors in `check_active_onboarding()`
- When workflow query fails (not NOT_FOUND), automatically terminate stale workflow
- Added `_terminate_stale_workflow()` helper function
- User can now continue with `/start` after deploy without manual intervention

## Root cause
When BuyerOnboardingWorkflow code changes after deploy, active workflows become incompatible.
Temporal tries to replay history with new code and fails with Nondeterminism error.
This blocked all webhook processing for affected users.

## Solution
- Detect query failures (RPC error or exception with "nondeterminism"/"does not handle")
- Automatically terminate the stale workflow with reason logged
- Return None from `check_active_onboarding()` to allow normal message processing
- User can restart onboarding with `/start`

## Test
```bash
make test-unit 2>&1 | tail -5
```

Expected: All tests pass (319 passed)
