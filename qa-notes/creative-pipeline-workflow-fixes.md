# Creative Pipeline Workflow Fixes

## Issue
При тестировании workflow транскрипции видео обнаружены проблемы:
1. Неправильный вызов `execute_activity()` с множественными позиционными аргументами
2. Type mismatch: `transcripts.id` (bigint) передавался как int вместо str
3. Activities пытались записать несуществующие колонки в БД

## Test Video
- URL: https://drive.google.com/file/d/19XD9v1pcat7GBlEMD26wU1k2C6KmPSiD/view
- Transcription: Spanish medical content about prostatitis
- Duration: ~10 seconds

## Fixes Applied

### 1. execute_activity args format (creative_pipeline.py)
```python
# Before (incorrect)
await workflow.execute_activity(
    transcribe_audio,
    audio_url,
    None,  # language_code
    start_to_close_timeout=...
)

# After (correct)
await workflow.execute_activity(
    transcribe_audio,
    args=[audio_url, None],
    start_to_close_timeout=...
)
```

### 2. transcript_id type conversion (creative_pipeline.py)
```python
# Before
saved_transcript_id = saved_transcript.get("id")  # Returns int

# After
saved_transcript_id = str(saved_transcript["id"])  # Converts to str
```

### 3. Removed non-existent columns from activities (supabase.py)
- `save_decomposed_creative`: removed `canonical_hash`, `transcript_id`
- `create_idea`: removed `buyer_id`

## Test Results
```
idea_id: 0629ea07-2ba6-4b7a-a69e-59b4affc81df
canonical_hash: 0370bb272b7455e2...
idea_status: active
decision: APPROVE
hypothesis_count: 3
```

## Pipeline Flow Verified
1. Transcription (AssemblyAI) - OK
2. Transcript save - OK
3. LLM Decomposition (OpenAI) - OK
4. Decomposed creative save - OK
5. Idea creation - OK
6. Decision Engine (APPROVE) - OK
7. Hypothesis generation (3) - OK
8. Hypothesis save - OK
9. Telegram delivery - SKIP (no chat_id for test buyer)

## Date
2026-01-11
