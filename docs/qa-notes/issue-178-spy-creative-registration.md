# QA Notes: Issue #178 - Spy Creative Registration

## Issue
Spy Creative Registration sends invalid `creative_id='unknown'` to decomposition workflow.

## Status
**RESOLVED** - Issue was already fixed before investigation.

## Root Cause (Historical)
Original workflow called decomposition webhook without first creating a record in `creatives` table.

## Fix Applied
Workflow `Spy Creative Registration` (pL6C4j1uiJLfVRIi) now:
1. `Insert Spy Creative` node creates record in `creatives` table first
2. Uses `$('Insert Spy Creative').first().json[0].id` for valid UUID
3. Passes UUID to transcription and decomposition workflows

## Verification
- Execution #2334: `Insert Spy Creative` returned valid UUID `b24c2454-4b1a-4fe1-b051-d22de0371f47`
- No records with `creative_id='unknown'` in `decomposed_creatives` table

## Edge Cases Discovered
1. **Telegram parse entities error** - If error message contains unescaped markdown, Telegram API returns 400
2. **404 from Call Transcription** - Multiple issues fixed:
   - Wrong workspace: `genomai.app.n8n.cloud` → `kazamaqwe.app.n8n.cloud`
   - Wrong path: `creative-transcription` → `genomai-transcribe`
   - Wrong method: GET → POST
3. **Parse Message не находит текст** - Входные данные `body.message.text`, а не `body.text`
4. **JSON parameter invalid** - Выражение `$json[0].id` неверно, должно быть `$json.id`

## Related Workflows
- `Spy Creative Registration` (pL6C4j1uiJLfVRIi)
- `creative_decomposition_llm` (mv6diVtqnuwr7qev)

## Constraints
- `creatives.id` is UUID type - cannot accept string "unknown"
- Foreign key constraint on `decomposed_creatives.creative_id` → `creatives.id`
