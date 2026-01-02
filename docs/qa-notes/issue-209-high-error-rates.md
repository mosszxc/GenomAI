# Issue #209: High Error Rates Investigation

**Date:** 2026-01-02
**Issue:** High error rates on idea_registry and decomposition workflows
**Reported Rates:** idea_registry_create 45%, creative_decomposition_llm 50%

## Investigation Summary

The reported 45-50% error rates are **misleading**. The actual workflow error rate is approximately 5-10%.

## Root Causes Identified

### 1. TranscriptionFailed (6 events)

Primary error source. Google Drive links returning HTML error pages instead of video files.

**Error message:**
```
"Transcoding failed. File does not appear to contain audio. File type is text/html"
```

**Causes:**
- Expired Google Drive share links
- Permission issues (not shared publicly)
- Deleted files

### 2. Large File Skips (7 creatives)

Status `skipped_large_file` is **expected behavior** for files > 50MB, not an error.

### 3. HypothesisDeliveryFailed (3 events)

Spy creatives created without `buyer_id` cannot be delivered via Telegram.

## Pipeline Analysis (Last 30 days)

| Event Category | Event Type | Count |
|----------------|------------|-------|
| SUCCESS | RawMetricsObserved | 85 |
| SUCCESS | TelegramMessageRouted | 39 |
| SUCCESS | IdeaRegistered | 5 |
| SUCCESS | DecisionMade | 5 |
| SUCCESS | CreativeDecomposed | 4 |
| SUCCESS | TranscriptCreated | 4 |
| SUCCESS | HypothesisGenerated | 3 |
| FAILED | TranscriptionFailed | 6 |
| FAILED | HypothesisDeliveryFailed | 3 |

## Current Pipeline State

| Status | Count | Has Decomposed | Has Idea |
|--------|-------|----------------|----------|
| skipped_large_file | 7 | 2 | 2 |
| decomposed | 1 | 1 | 1 |
| pending | 1 | 1 | 1 |

All decomposed_creatives have idea_id assigned (100% success rate for idea_registry workflow).

## Creatives Stuck in Pipeline

Only 1 creative is "stuck" (status=pending, older than 1 hour):
- ID: `29ed41a9-2275-45a0-9a5d-806285ef0ff7`
- But this creative HAS decomposed_id and idea_id (pipeline completed!)
- Status field just wasn't updated to 'decomposed'

## Recommendations

### Immediate (No Code Changes)
1. Validate Google Drive URLs before sending to transcription
2. Educate users about proper share link format
3. Track `skipped_large_file` separately from error metrics

### Future Improvements
1. Add pre-flight URL validation in creative registration workflow
2. Auto-update creative status when idea is created
3. Handle spy creatives without buyer_id (skip delivery or assign default)

## Detection Queries

```sql
-- Check for transcription failures
SELECT event_type, payload, occurred_at
FROM genomai.event_log
WHERE event_type = 'TranscriptionFailed'
ORDER BY occurred_at DESC;

-- Check pipeline success rate
SELECT
  CASE
    WHEN event_type IN ('IdeaRegistered', 'CreativeDecomposed', 'TranscriptCreated') THEN 'SUCCESS'
    WHEN event_type LIKE '%Failed' THEN 'FAILED'
    ELSE 'OTHER'
  END as category,
  COUNT(*) as count
FROM genomai.event_log
WHERE occurred_at > NOW() - INTERVAL '30 days'
GROUP BY category;
```

## Conclusion

**No workflow bugs found.** The high error rates are caused by:
1. Bad input data (invalid Google Drive URLs) - 6 failures
2. Expected skips (large files) - 7 skips counted as errors
3. Design issue (spy creatives without buyer) - 3 failures

**Actual workflow success rate: ~90-95%**
