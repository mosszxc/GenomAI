# QA Notes: Spy Creative Registration - Decomposition Fix

## Issue
#178 - Spy Creative Registration sends invalid `creative_id='unknown'` to decomposition

## Root Cause
Node `Call Decomposition` in workflow `pL6C4j1uiJLfVRIi`:
- Was making **GET** request (no body)
- Did not pass `creative_id`, `transcript_text`, or `is_spy` flag

## Fix Applied
Updated `Call Decomposition` node parameters:
```json
{
  "method": "POST",
  "url": "https://kazamaqwe.app.n8n.cloud/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sendBody": true,
  "specifyBody": "json",
  "contentType": "json",
  "jsonBody": "={{ JSON.stringify({ creative_id: $('Insert Spy Creative').first().json.id, transcript_text: ($('Fetch Transcript').first().json[0] && $('Fetch Transcript').first().json[0].transcript_text) || 'SPY_PLACEHOLDER - requires manual transcription', is_spy: true }) }}"
}
```

## Key Changes
1. **Method**: GET → POST
2. **Body**: Added with proper structure:
   - `creative_id`: UUID from Insert Spy Creative node
   - `transcript_text`: From Fetch Transcript or fallback placeholder
   - `is_spy: true`: Forces `source_type='spy'` in decomposition

## Validation
- Workflow validates successfully (0 errors, 21 warnings)
- Warnings are non-critical (chatId format, error handling suggestions)
- Recent executions show 4/5 success rate

## Edge Cases
- If transcription fails, uses placeholder text
- `is_spy: true` ensures downstream `creative_decomposition_llm` marks source_type correctly

## Testing Notes
- Cannot directly test via n8n_test_workflow (requires Telegram webhook trigger)
- Real test: Send `spy <URL>` message via Telegram to registered buyer
- Verify: Check `decomposed_creatives` table for new spy records

## Related
- Workflow: `Spy Creative Registration` (pL6C4j1uiJLfVRIi)
- Downstream: `creative_decomposition_llm` (mv6diVtqnuwr7qev)
