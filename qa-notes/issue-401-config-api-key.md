# QA Notes: Issue #401 - decision_engine_api_key missing from genomai.config

## Summary
Added missing `decision_engine_api_key` to `genomai.config` table.

## Changes
- INSERT into `genomai.config`: `decision_engine_api_key` with `is_secret=true`

## Verification

### Before
```sql
SELECT key FROM genomai.config WHERE key LIKE '%decision_engine%';
-- Result: only decision_engine_api_url
```

### After
```sql
SELECT key, is_secret FROM genomai.config WHERE key LIKE '%decision_engine%';
```
| key | is_secret |
|-----|-----------|
| decision_engine_api_url | false |
| decision_engine_api_key | true |

## Production Test: PASSED

**Command:**
```sql
INSERT INTO genomai.config (key, value, is_secret, description)
VALUES ('decision_engine_api_key', '***', true, 'API key for Decision Engine authentication');
```

**Result:** Row inserted, verified with SELECT query.

## Impact
Decision Engine authentication now has API key available in config.
