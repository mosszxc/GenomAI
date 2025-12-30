# QA Notes: Issue #183 - Double-encoded JSON payload

## Problem
`decomposed_creatives.payload` stored as JSON string instead of JSONB object.

## Root Cause
`Persist Decomposed Creative` node used `JSON.stringify()` on payload field. Supabase node already serializes objects to JSONB, causing double-encoding.

## Detection
E2E skill `--quality` check found:
```sql
jsonb_typeof(payload) = 'string'  -- should be 'object'
```

## Fix Applied
1. Removed `JSON.stringify()` wrapper from payload expression
2. Fixed corrupted record: `SET payload = (payload #>> '{}')::jsonb`

## Edge Cases
- `#>> '{}'` operator extracts JSONB string value as text (removes outer quotes)
- Direct `::text::jsonb` cast doesn't work for double-encoded strings

## Verification
```sql
SELECT jsonb_typeof(payload), payload->>'angle_type'
FROM genomai.decomposed_creatives
WHERE id = '0bf57a08-bbc3-484e-b163-f657760b6aea';
-- Returns: 'object', 'fear'
```

## Prevention
Never use `JSON.stringify()` when passing objects to Supabase n8n node JSONB fields.
