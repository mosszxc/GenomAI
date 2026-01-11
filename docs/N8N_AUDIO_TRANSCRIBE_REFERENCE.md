# N8N AudioTranscribe Workflow Reference

Эталонный документ для workflow транскрибации аудио/видео в GenomAI.

## Overview

| Параметр | Значение |
|----------|----------|
| **Workflow ID** | `zwtqav0d2R35zQot` |
| **Webhook Path** | `7c271222-3707-4797-aaf1-6d39b8155e9a` |
| **Сервис транскрипции** | AssemblyAI |
| **Целевая таблица** | `genomai.transcripts` |

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  POST Webhook                                                       │
│  body: { AudioID, id }                                              │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Download     │ ◄── Google Drive (AudioID)                        │
│  │ file         │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐     error    ┌─────────┐                          │
│  │ Upload to    │─────────────►│ Wait    │──┐                       │
│  │ AssemblyAI   │              │ 1 min   │  │                       │
│  └──────┬───────┘              └─────────┘  │                       │
│         │ success                     ▲     │                       │
│         │                             └─────┘ retry                 │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Start        │ language_detection: true                          │
│  │ Transcription│ speaker_labels: true                              │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Get Result   │◄─────────────────────────────┐                    │
│  └──────┬───────┘                              │                    │
│         │                                      │                    │
│         ▼                                      │                    │
│  ┌──────────────┐                       ┌──────┴───┐                │
│  │ Switch       │──processing/queued───►│ Wait 30s │                │
│  │ (status)     │                       └──────────┘                │
│  └──────┬───────┘                                                   │
│         │                                                           │
│    ┌────┴────┐                                                      │
│    │         │                                                      │
│    ▼         ▼                                                      │
│ completed   error                                                   │
│    │         │                                                      │
│    ▼         ▼                                                      │
│ ┌────────┐ ┌────────┐                                               │
│ │ Update │ │ Switch │──"no spoken audio"──► Update (error)          │
│ │ success│ │ error  │                                               │
│ └────────┘ └────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Webhook Input

```json
{
  "body": {
    "AudioID": "string",  // Google Drive file ID
    "id": "uuid"          // genomai.transcripts.id
  }
}
```

## AssemblyAI Integration

### Upload Endpoint
```
POST https://api.assemblyai.com/v2/upload
Headers:
  authorization: <API_KEY>
Body: multipart/form-data (audio file)
Response: { "upload_url": "..." }
```

### Transcription Endpoint
```
POST https://api.assemblyai.com/v2/transcript
Headers:
  authorization: <API_KEY>
  content-type: application/json
Body:
{
  "audio_url": "<upload_url>",
  "speed_boost": false,
  "language_detection": true,
  "speaker_labels": true
}
Response: { "id": "transcript_id", "status": "queued" }
```

### Polling Endpoint
```
GET https://api.assemblyai.com/v2/transcript/{id}
Headers:
  authorization: <API_KEY>
Response: { "id": "...", "status": "completed|processing|queued|error", "text": "..." }
```

## Status Flow

| Status | Action |
|--------|--------|
| `queued` | Wait 30s → poll again |
| `processing` | Wait 30s → poll again |
| `completed` | Save transcript → set TranslateStatus=queued |
| `error` | Check error type → save error status |

## Database Updates

### Success Case
```sql
UPDATE genomai.transcripts
SET
  transcript_text = '<result.text>',
  "TranscribeStatus" = 'finish',
  "TranslateStatus" = 'queued'
WHERE id = '<webhook.body.id>';
```

### Error Case (Empty Audio)
```sql
UPDATE genomai.transcripts
SET
  transcript_text = 'Звуковой файл пустой.',
  "TranscribeStatus" = 'error'
WHERE id = '<webhook.body.id>';
```

## Credentials Required

| Service | Credential Name | Type |
|---------|-----------------|------|
| Google Drive | "Google Main" | OAuth2 |
| AssemblyAI | (hardcoded) | API Key |
| Supabase | "Main" | API Key |

## Retry Logic

1. **Upload Failure**: 1 minute wait → retry upload
2. **Transcription Pending**: 30 second polling interval

## Error Handling

| Error | Handling |
|-------|----------|
| `language_detection cannot be performed on files with no spoken audio` | Set status=error, text="Звуковой файл пустой" |
| Upload timeout | Retry after 1 min |
| Other errors | Passed through Switch3 (no action defined) |

## Table Schema Reference

```sql
-- genomai.transcripts (relevant columns)
id              UUID PRIMARY KEY
transcript_text TEXT
"TranscribeStatus" TEXT  -- queued, processing, finish, error
"TranslateStatus"  TEXT  -- queued, processing, finish, error
```

## Integration Points with GenomAI

| Step | GenomAI Component |
|------|-------------------|
| Trigger | Video Ingestion Pipeline triggers webhook |
| Output | `TranslateStatus=queued` triggers translation workflow |
| Data | `transcript_text` used by LLM for idea extraction |

## Raw Workflow JSON

Оригинальный файл: `/Users/mosszxc/Downloads/AudioTranscribe.json`

Импорт в n8n:
1. Settings → Import from File
2. Выбрать JSON файл
3. Настроить credentials

## Future Improvements

- [ ] Вынести API ключ в credentials (не hardcode)
- [ ] Добавить обработку всех типов ошибок
- [ ] Добавить timeout для бесконечного polling
- [ ] Интегрировать с Temporal для tracking
