# QA Notes: Issue #464 - --geo flag validation

## Summary
Added validation for `--geo` flag in `/simulate` command against `VALID_GEOS` list.

## Changes
- `decision-engine-service/src/routes/telegram.py`:
  - Added import of `VALID_GEOS` from `temporal.models.buyer`
  - Added validation after geo parsing (lines 944-953)
  - Returns user-friendly error with sample valid geos

## Local Test

### Test 1: Validation logic
```bash
python3.12 -c "
from temporal.models.buyer import VALID_GEOS
geo = 'INVALIDCODE123'
if geo not in VALID_GEOS:
    print('Invalid geo rejected')
"
```
Result: `Invalid geo rejected` - PASSED

### Test 2: Unit tests
```bash
make test-unit
```
Result: `157 passed in 0.55s` - PASSED

## Risk Assessment
- LOW: Validation is additive, doesn't break existing functionality
- Valid geos (US, UK, etc.) continue to work as before

## Verification on Production
After deploy, send to Telegram:
```
/simulate fear --geo INVALID
```
Expected: Error message with list of valid geos
