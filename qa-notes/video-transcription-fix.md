# Video Transcription MIME Type Fix

## Problem
AssemblyAI rejected video uploads with error:
```
Transcoding failed. File does not appear to contain audio.
File type is application/octet-stream (data).
```

## Root Cause
- n8n HTTP Request node sent binary data as `multipart-form-data`
- AssemblyAI upload endpoint expects raw binary with correct Content-Type
- MIME type from Google Drive download was lost in transfer

## Solution
Changed `Upload to AssemblyAI` node:
- `contentType`: `multipart-form-data` → `binaryData` (raw binary)
- Added `Content-Type` header: `={{ $binary.data.mimeType }}`

## Workflow
`GenomAI - Video Transcription` (pUjbKD9BUJktTdQ6)

## Test Result
- Video: 56MB MP4 (Spanish audio)
- Transcription: completed in ~30 sec
- Transcript saved to `genomai.transcripts`
