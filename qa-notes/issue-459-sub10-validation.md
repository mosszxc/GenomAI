# Issue #459: Add sub10 validation during buyer onboarding

## Summary
Added validation for sub10 input during buyer onboarding workflow to prevent silent failures when incorrect sub10 is entered.

## Changes
- **File**: `decision-engine-service/temporal/workflows/buyer_onboarding.py`
- Added import for `get_campaigns_by_source` and `GetCampaignsBySourceInput` from keitaro activities
- Added `MAX_SUB10_RETRY_ATTEMPTS = 3` constant
- Added new messages: `validating_sub10`, `sub10_found`, `sub10_not_found`, `sub10_retries_exhausted`
- Modified Step 4 (AWAITING_KEITARO) to validate sub10 by querying Keitaro API
- Added retry loop with 3 attempts for invalid sub10

## Behavior
| Input | Old Behavior | New Behavior |
|-------|--------------|--------------|
| Valid sub10 | Silent proceed | Shows "Found N campaigns", proceeds |
| Invalid sub10 | Silent 0 campaigns | Shows error, asks for retry (3 attempts) |
| 3 failed attempts | N/A | Cancels onboarding with error message |

## Tests
- Unit tests: PASSED (CI)
- Health check: PASSED

## Production Test
- Type: Health check API
- Command: `curl -s https://genomai.onrender.com/health`
- Result: `{"status":"ok"}`
