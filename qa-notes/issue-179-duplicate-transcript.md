# Issue #179: Duplicate Transcript Insert Fix

## Edge Cases
- Workflow called twice for same creative_id → now silently ignores duplicate
- Empty response from UPSERT when record exists (PostgREST returns empty array with `resolution=ignore-duplicates`)
- Downstream nodes (`Emit TranscriptCreated`) may receive empty data when duplicate skipped

## Gotchas
- `$generateUUID()` inside `JSON.stringify()` doesn't work in n8n expressions
- PostgREST `on_conflict` requires column names, not constraint name
- `id` column type is UUID - cannot use composite keys like `creative_id-v1`
- Supabase node doesn't support UPSERT - must use HTTP Request

## Constraints
- `transcripts` table has UNIQUE constraint on `(creative_id, version)`
- `id` column has DEFAULT gen_random_uuid() - can omit from INSERT
- Must include `Content-Profile: genomai` header for schema routing

## Dependencies
- `creative_decomposition_llm` workflow calls `idea_registry_create` downstream
- Transcript must exist before `decomposed_creatives` can reference it
