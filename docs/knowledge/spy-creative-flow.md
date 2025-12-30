# Knowledge: Spy Creative Flow

## Overview
SPY креативы - это креативы конкурентов, которые пользователь отправляет для анализа паттернов.

## Flow
```
Telegram "spy <URL>"
    → Router Webhook
    → Parse Message
    → Validate Input
    → Check Buyer Registered
    → Insert Spy Creative (creatives table)
    → Emit SpyCreativeRegistered (event_log)
    → Reply Analyzing
    → Call Transcription
    → Fetch Transcript
    → Call Decomposition
    → Reply Complete
```

## Key Differences from Regular Creatives
| Aspect | Regular Creative | Spy Creative |
|--------|------------------|--------------|
| `tracker_id` | Required (Keitaro) | `null` |
| `source_type` | `internal` | `spy` |
| `is_spy` flag | `false` | `true` |
| Decision Engine | Full 4-check flow | Skipped |
| Hypothesis | Created | Not created |

## Workflows
- **Spy Creative Registration** (pL6C4j1uiJLfVRIi) - Entry point
- **creative_decomposition_llm** (mv6diVtqnuwr7qev) - LLM classification

## Data Flow
1. `creatives` table: `source_type = 'spy'`, `tracker_id = null`
2. `transcripts` table: standard transcript
3. `decomposed_creatives` table: `payload.source_type = 'spy'` (forced by Schema Validation)

## Important Implementation Details

### Insert Before Decomposition
**CRITICAL**: Always INSERT into `creatives` table BEFORE calling decomposition.
- `decomposed_creatives.creative_id` has FK constraint to `creatives.id`
- UUID must be valid, not "unknown" or placeholder

### is_spy Flag Propagation
- Set in `Parse Message` node: `is_spy: true`
- Passed to decomposition webhook body
- `Load Canonical Schema` extracts it: `body.is_spy === true`
- `Schema Validation` forces `source_type = 'spy'` when flag is true

### Webhook URLs
Current active endpoints:
- Transcription: `https://kazamaqwe.app.n8n.cloud/webhook/creative-transcription`
- Decomposition: `https://genomai.app.n8n.cloud/webhook/decompose/creative`

## Common Issues

### "creative_id: unknown" Error
**Cause**: Workflow called decomposition before INSERT into creatives.
**Fix**: Ensure `Insert Spy Creative` node runs first and use its returned `id`.

### Telegram Parse Error
**Cause**: Unescaped markdown in error messages.
**Fix**: Use `parseMode: "None"` in Telegram nodes for error messages.
