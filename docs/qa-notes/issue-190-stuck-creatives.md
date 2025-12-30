# QA Notes: Issue #190 - Stuck Creatives in Transcription

## Problem
12 creatives were stuck in transcription stage, blocking the pipeline.

## Root Cause
1. **Non-Drive URLs**: Workflow expected Google Drive URLs but received TikTok/test URLs
2. **Empty file ID**: Regex `match(/\/d\/([a-zA-Z0-9_-]+)/)` returned empty string for non-Drive URLs
3. **Cascade failure**: Get File Size failed → Check File Size returned 0 items → Get Buyer tried with empty buyer_id → crash

## Fix Applied
Added `Check URL Type` node between `IF Transcript Exists` and `Get File Size`:
- **True branch** (Drive URL): Continues to Get File Size → normal transcription flow
- **False branch** (Non-Drive URL): Updates status to `unsupported_source`

## Stuck Creatives Resolution
| Type | Count | Resolution |
|------|-------|------------|
| Test/fake URLs | 7 | Marked as `unsupported_source` |
| Large files (>50MB) | 2 | Marked as `skipped_large_file` |
| Duplicates with error | 2 | Already marked as `error` |
| Already skipped | 1 | Already marked as `skipped_large_file` |

## Test Results
- Workflow execution: SUCCESS
- Get Buyer node: Now works correctly (previously crashed)
- Telegram notifications: Sent to buyer and admin
- DB status update: Correctly set to `skipped_large_file`

## Edge Cases
1. URLs with `drive.google.com` but invalid file ID → Will fail at Get File Size (needs error handling)
2. TikTok URLs → Marked as unsupported (need separate workflow for social media)

## Workflow Changes
- Added nodes: `Check URL Type`, `Update Status Unsupported`
- Modified connection: `IF Transcript Exists` → `Check URL Type` → `Get File Size`

## Verification Query
```sql
SELECT status, COUNT(*)
FROM genomai.creatives
WHERE NOT EXISTS (SELECT 1 FROM genomai.transcripts WHERE creative_id = creatives.id)
GROUP BY status;
-- Expected: no 'registered' status for creatives that went through workflow
```
