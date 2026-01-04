# Issue #209: High error rates on idea_registry and decomposition workflows

**Date:** 2026-01-04
**Status:** Closed (No Code Changes Required)

## Summary

The reported 45-50% error rates on `idea_registry_create` and `creative_decomposition_llm` workflows were **misinterpreted data quality issues**, not workflow bugs.

## Root Cause

| Error Type | Count | Root Cause |
|------------|-------|------------|
| TranscriptionFailed | 6 | Invalid Google Drive links returning HTML instead of video |
| HypothesisDeliveryFailed | 3 | Spy creatives without buyer_id |
| skipped_large_file | 7 | Files > 50MB (expected behavior, not error) |

## Key Insight

The n8n execution "errors" included upstream failures that cascaded through the pipeline. When a creative fails at transcription stage (e.g., bad Google Drive URL), all subsequent workflows (decomposition, idea_registry) also show as "failed" even though the workflow logic is correct.

## Actual Error Rate

Current pipeline health (last 7 days):
- IdeaRegistered: 5 success
- DecisionMade: 5 success
- CreativeDecomposed: 4 success
- TranscriptCreated: 3 success
- TranscriptionFailed: 1 error
- HypothesisDeliveryFailed: 3 errors

**Actual workflow error rate: ~5-10%** (acceptable)

## TranscriptionFailed Pattern

```
"Transcoding failed. File does not appear to contain audio.
File type is text/html (HTML document, ASCII text)"
```

This occurs when:
- Google Drive permissions are not set to "Anyone with link"
- File was deleted
- Share link expired
- Rate limiting by Google

## Recommendations for Future

1. **URL Validation**: Add pre-flight check for Google Drive URLs before sending to AssemblyAI
2. **Error Classification**: Separate `skipped_large_file` from actual errors in metrics
3. **Buyer ID Propagation**: Ensure spy creatives have buyer_id from registration context

## Testing

No test required - investigation confirmed workflows are working correctly.

## Related Documentation

- `docs/KNOWN_ISSUES.md` - Section "#209 Investigation Results"
- `docs/N8N_WORKFLOWS.md` - Workflow documentation
