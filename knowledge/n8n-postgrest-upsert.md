# n8n + PostgREST UPSERT Pattern

## Problem
Supabase nodes in n8n don't support UPSERT (ON CONFLICT). When workflow runs multiple times with same data, INSERT fails with duplicate key violation.

## Solution: HTTP Request with PostgREST UPSERT

### Configuration
```
Node: HTTP Request
Method: POST
URL: https://{project}.supabase.co/rest/v1/{table}?on_conflict={columns}
Authentication: predefinedCredentialType → supabaseApi
Headers:
  - Content-Profile: {schema}  (e.g., "genomai")
  - Prefer: resolution=ignore-duplicates,return=representation
Body: JSON with fields (exclude id if has DEFAULT)
```

### Key Points

1. **on_conflict parameter**: Comma-separated column names that have UNIQUE constraint
   - Example: `?on_conflict=creative_id,version`
   - Uses columns, NOT constraint name

2. **Prefer header options**:
   - `resolution=ignore-duplicates` → ON CONFLICT DO NOTHING (skip duplicates)
   - `resolution=merge-duplicates` → ON CONFLICT DO UPDATE (overwrite)
   - `return=representation` → return inserted/updated rows

3. **Omit auto-generated fields**: If `id` has `DEFAULT gen_random_uuid()`, don't include it

4. **Empty response on skip**: When duplicate is skipped, PostgREST returns empty array `[]`

## Alternatives Considered

- **Check before insert**: Extra query, race condition possible
- **Try-catch on duplicate**: Error handling complex, breaks flow
- **UPSERT via SQL function**: More setup, harder to maintain

## When to Use
- Idempotent workflows that may be retried
- Data ingestion from external sources
- Any INSERT that could be called twice with same unique key
