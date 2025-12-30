# Video Transcription MIME Type Fix

## Status: OBSOLETE

**Workflow `GenomAI - Video Transcription` (pUjbKD9BUJktTdQ6) has been DELETED.**

Reason: Orphaned workflow without callers. Was a duplicate of `GenomAI - Creative Transcription` but without file size safety checks, which caused out-of-memory crashes on large files.

## Current Workflow
Use `GenomAI - Creative Transcription` (WMnFHqsFh8i7ddjV) for all transcription:
- Webhook: `genomai-transcribe`
- Has file size validation (max 100MB)
- Has URL type validation
- Has error notifications

---

## Historical Context (for reference)

### Original Problem
AssemblyAI rejected video uploads with error:
```
Transcoding failed. File does not appear to contain audio.
File type is application/octet-stream (data).
```

### Original Solution
Changed `Upload to AssemblyAI` node:
- `contentType`: `multipart-form-data` -> `binaryData` (raw binary)
- Added `Content-Type` header: `={{ $binary.data.mimeType }}`

This fix is already applied in Creative Transcription workflow.
