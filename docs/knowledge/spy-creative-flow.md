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
**IMPORTANT**: All n8n webhooks use workspace `kazamaqwe.app.n8n.cloud`

| Endpoint | Workflow | Path | Full URL |
|----------|----------|------|----------|
| Transcription | GenomAI - Creative Transcription | `genomai-transcribe` | `https://kazamaqwe.app.n8n.cloud/webhook/genomai-transcribe` |
| Decomposition | creative_decomposition_llm | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | `https://kazamaqwe.app.n8n.cloud/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| Idea Registry | idea_registry_create | `idea-registry-create` | `https://kazamaqwe.app.n8n.cloud/webhook/idea-registry-create` |

**WARNING**: `genomai.app.n8n.cloud` is deprecated/non-existent. Always use `kazamaqwe.app.n8n.cloud`.

## Common Issues

### "creative_id: unknown" Error
**Cause**: Workflow called decomposition before INSERT into creatives.
**Fix**: Ensure `Insert Spy Creative` node runs first and use its returned `id`.

### Telegram Parse Error
**Cause**: Unescaped markdown in error messages.
**Fix**: Use `parseMode: "None"` in Telegram nodes for error messages.

### 404 from Call Transcription
**Cause**: Wrong workspace URL or webhook path.
**Fix**:
- Use `kazamaqwe.app.n8n.cloud` (NOT `genomai.app.n8n.cloud`)
- Use correct path `genomai-transcribe` (NOT `creative-transcription`)
- Use POST method (NOT GET)

### Parse Message не находит текст
**Cause**: Входящие данные имеют структуру `body.message.text`, а не `body.text`.
**Fix**: Добавить fallback в Parse Message:
```javascript
const messageText = routerData.raw?.message?.text || routerData.message?.text || routerData.text || '';
const chatId = routerData.message?.chat?.id || routerData.chat_id;
const userId = routerData.message?.from?.id?.toString() || routerData.telegram_id;
```

### "JSON parameter needs to be valid JSON" в Call Transcription
**Cause**: Неверное выражение `$json[0].id` вместо `$json.id`.
**Fix**: Supabase с `return=representation` возвращает объект напрямую:
```javascript
// Неверно
$('Insert Spy Creative').first().json[0].id

// Верно
$('Insert Spy Creative').first().json.id
```

### 401 Unauthorized в Fetch Transcript
**Cause**: Отсутствует apikey header при запросе к Supabase.
**Fix**: Добавить headers (уже исправлено в workflow):
```
apikey: <anon_key>
Authorization: Bearer <anon_key>
Accept-Profile: genomai
```
