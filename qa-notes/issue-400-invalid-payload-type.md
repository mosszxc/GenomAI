# QA Notes: Issue #400 - Invalid payload type in decomposed_creatives

## Problem
2 records in `decomposed_creatives` had `payload` stored as JSON string instead of JSON object (double-encoded).

## Root Cause
`save_decomposed_creative` activity in `temporal/activities/supabase.py:325`:
```python
"payload": json.dumps(payload) if isinstance(payload, dict) else payload,
```

Supabase REST API already serializes the request body as JSON. Using `json.dumps()` caused double-encoding.

## Fix
1. Removed `json.dumps()` - pass dict directly
2. Added validation: `if not isinstance(payload, dict): raise ValueError(...)`
3. Fixed existing records: `UPDATE ... SET payload = (payload #>> '{}')::jsonb WHERE jsonb_typeof(payload) = 'string'`

## Test Results

### Data verification
```sql
SELECT COUNT(*) as invalid_count
FROM genomai.decomposed_creatives
WHERE jsonb_typeof(payload) != 'object' OR payload IS NULL;
-- Result: 0 (was 2)
```

### Unit tests
```
make test → 35 passed in 0.92s
```

### Production test (after deploy)
```bash
curl -s https://genomai.onrender.com/health
# → {"status":"ok","timestamp":"2026-01-11T16:05:04.304881"}
```

```sql
SELECT total, valid_objects, invalid FROM genomai.decomposed_creatives;
-- Result: total=3, valid_objects=3, invalid=0
```

**PASSED**

## PR
https://github.com/mosszxc/GenomAI/pull/413 (merged)
