# QA Notes: Issue #184 - Stuck Creatives Without Decomposition

## Problem
2 creatives had transcripts but no `decomposed_creatives` records - stuck in pipeline at "transcribed" status.

## Affected Creatives
| creative_id | status_before | decomposed_id | idea_id |
|-------------|---------------|---------------|---------|
| `99acb25b-2f75-457c-bdfc-a7d0e3d091ac` | transcribed | `3c3f21f9-fb7a-409e-bbd1-47eb64b4f463` | `42c6f800-bddd-4fe5-982b-5bcf796a6ebe` |
| `b5ea7452-9bae-4aec-a7d9-77b1235f3d73` | transcribed | `9ddb15d1-80cf-42d5-9478-0beb413dd411` | `80aeb676-ed02-4d4a-a1f6-3970b1d9472a` |

## Root Cause
Transcription workflow (`GenomAI - Creative Transcription`) completed but didn't trigger decomposition webhook. Likely one-time network/timeout failure.

## Fix Applied
1. Manually triggered `creative_decomposition_llm` workflow via webhook
2. Updated creative status from "transcribed" to "decomposed"

## Validation Query
```sql
-- Check for stuck creatives (should return 0 rows now)
SELECT c.id, c.status
FROM genomai.creatives c
INNER JOIN genomai.transcripts t ON t.creative_id = c.id
WHERE NOT EXISTS (
  SELECT 1 FROM genomai.decomposed_creatives dc WHERE dc.creative_id = c.id
);
```

## Decomposition Webhook Details
- Workflow ID: `mv6diVtqnuwr7qev`
- Path: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- Required payload: `{creative_id, transcript_text}`
- Optional: `is_spy: true` for spy creatives

## Gotchas
1. Transcripts are stored in separate `transcripts` table, not in `creatives`
2. Decomposition workflow also creates transcript record (with `on_conflict=ignore-duplicates`)
3. Workflow calls idea_registry_create after decomposition - full pipeline runs

## Prevention
Pipeline Health Monitor workflow (`H1uuOanSy627H4kg`) should detect these cases.
