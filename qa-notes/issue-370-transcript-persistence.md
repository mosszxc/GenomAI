# QA Notes: Issue #370 - Persist Transcripts Before Decomposition

**Date:** 2026-01-11
**Status:** Implemented

## Problem

Транскрипты из AssemblyAI не сохранялись в БД. При падении decomposition:
- Приходилось платить за повторную транскрибацию (2-10 мин + $$$)
- Текст терялся после workflow

## Solution

Добавлена персистентность транскриптов в таблицу `genomai.transcripts` с recovery path.

### New Flow

```
Creative → Check existing transcript?
         ┌──────────┴──────────┐
         │ YES                 │ NO
         ↓                     ↓
    Use existing         AssemblyAI → save_transcript()
    transcript               │
         └─────────┬─────────┘
                   ↓
            Decomposition (if fails, next retry uses saved transcript)
```

## Changes Made

### 1. Migration 037_transcript_assemblyai_id.sql
- Added `assemblyai_transcript_id` column to `transcripts` table
- Created partial index for lookups

### 2. New Activities (supabase.py)
- `save_transcript(creative_id, transcript_text, assemblyai_transcript_id)` — saves with version management
- `get_existing_transcript(creative_id)` — retrieves latest transcript for recovery

### 3. Updated CreativePipelineWorkflow
- Step 2 now checks for existing transcript first
- If exists → skip AssemblyAI (saves time & money)
- If not → transcribe → save → continue
- `saved_transcript_id` passed to decomposed_creatives instead of AssemblyAI ID

### 4. Registered in worker.py
Both `save_transcript` and `get_existing_transcript` registered in creative_worker activities.

## Verification

```sql
-- Check column exists
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = 'transcripts'
AND column_name = 'assemblyai_transcript_id';

-- Result: assemblyai_transcript_id | text ✓
```

```bash
# Syntax check
python3 -m py_compile temporal/activities/supabase.py
# Result: OK ✓
```

## Testing Notes

Full E2E testing requires:
1. Create creative with video_url
2. Trigger CreativePipelineWorkflow
3. Verify transcript saved to DB
4. Force-fail decomposition
5. Re-run workflow
6. Verify: uses existing transcript, no AssemblyAI call

## Benefits

- **Cost savings:** No duplicate AssemblyAI calls on retry
- **Time savings:** Recovery skips 2-10 min transcription
- **Audit trail:** AssemblyAI ID stored for traceability
- **Versioning:** Multiple transcript versions per creative supported
