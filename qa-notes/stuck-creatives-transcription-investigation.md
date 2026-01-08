# QA Notes: Stuck Creatives in Transcription Stage

## Issue
#190 - 12 creatives stuck in transcription stage

## Investigation Results

### Initial Findings
12 creatives found with `status IN ('pending', 'downloading', 'transcribing', 'processing')`:
- 7 creatives with test/fake URLs (non-existent files)
- 5 creatives with real Google Drive files (>50MB)

### Root Cause Analysis

**Test Data (7 creatives):**
- URLs like `test-url-1`, `test-url-2`, `https://test.com/video.mp4`
- Created during development/testing, never cleaned up
- Resolution: Deleted from database

**Large Files (5 creatives):**
- Real Google Drive files exceeding 50MB
- **Internal workflow limit:** 50MB (node `Check File Size`)
- **Note:** AssemblyAI API supports up to 5GB - limit is our choice, not API restriction
- Resolution: Workflow correctly marks them as `skipped_large_file`

### Workflow Behavior (Expected)
When file exceeds 50MB limit:
1. Downloads file and checks size
2. Sets `status: 'skipped_large_file'`
3. Creates alert in `#genomai-alerts` channel
4. Notifies buyer via Telegram to compress and re-upload

### Final Status
After retriggering transcription for 5 real creatives:
```
id: 94917afb-... | status: skipped_large_file | reason: file_too_large
id: c1527f88-... | status: skipped_large_file | reason: file_too_large
id: 55e6a7a5-... | status: skipped_large_file | reason: file_too_large
id: 17fb8ead-... | status: skipped_large_file | reason: file_too_large
id: 2f14a0e9-... | status: skipped_large_file | reason: file_too_large
```

## Conclusion
**This is NOT a bug.** The workflow is working as designed:
- Test data was cleaned up
- Large files are correctly identified and users are notified
- No code changes required

## Detection Query
```sql
-- Find actually stuck creatives (not skipped)
SELECT id, tracker_id, status, video_url
FROM genomai.creatives
WHERE status IN ('pending', 'downloading', 'transcribing', 'processing')
AND created_at < NOW() - INTERVAL '1 hour';

-- Find skipped large files (expected)
SELECT id, status, error_reason
FROM genomai.creatives
WHERE status = 'skipped_large_file';
```

## Prevention
1. Regular cleanup of test data in staging
2. Document 50MB file size limit in buyer onboarding
3. Consider increasing limit (AssemblyAI supports up to 5GB)

## Related
- Workflow: `Creative Transcription` (WMnFHqsFh8i7ddjV)
- Transcription API: **AssemblyAI** (not Whisper)
- Internal limit: 50MB (configurable in node `Check File Size`)
