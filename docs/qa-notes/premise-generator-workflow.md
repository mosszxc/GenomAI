# Premise Generator Workflow

## Overview
Workflow ID: `x2Udd72hNe0ODduu`
Created: 2026-01-02

Generates new premises via LLM (GPT-4o-mini) when the system needs fresh narrative vehicles. Supports both scheduled generation (weekly) and on-demand via webhook.

## Triggers

### 1. Schedule Trigger (Weekly)
- **When:** Every Monday at 09:00 UTC
- **Behavior:** Auto-selects underexplored premise_type, generates 3 premises

### 2. Webhook Trigger (On-Demand)
- **Path:** POST `/webhook/premise-generator`
- **Request Body:**
```json
{
  "premise_type": "method",  // Optional - auto-select if omitted
  "vertical": "nutra",       // Optional, default: "nutra"
  "geo": "RU",               // Optional, default: "RU"
  "count": 3                 // Optional, default: 1
}
```

## Flow

```
Trigger --> Merge Triggers --> [Parallel: Get Underexplored Type + Count By Type Fallback]
    --> Determine Target Type --> Load Winning Premises (for context)
    --> Format LLM Prompt --> Call OpenAI (gpt-4o-mini)
    --> Parse Response --> Check Parse Success
        |-- [SUCCESS] --> Loop Premises --> Check Unique
        |       |-- [UNIQUE] --> Insert Premise --> Emit PremiseGenerated --> Track Created --> Back to Loop
        |       |-- [DUPLICATE] --> Track Skipped --> Back to Loop
        |   --> [LOOP DONE] --> Aggregate Results --> Build Response --> Respond Success
        |-- [ERROR] --> Respond Error
```

## Valid premise_types (8 types)

1. **method** - A specific technique or ritual (e.g., "lemon seed method", "2-minute morning routine")
2. **discovery** - A revelation or finding (e.g., "ancient Tibetan discovery", "accidental lab finding")
3. **confession** - An insider admission (e.g., "doctor's confession", "pharma whistleblower")
4. **secret** - Hidden information (e.g., "suppressed remedy", "what they don't want you to know")
5. **ingredient** - A specific compound (e.g., "single kitchen ingredient", "forgotten herb")
6. **mechanism** - Root cause explanation (e.g., "hidden trigger", "real reason behind...")
7. **breakthrough** - New research/science (e.g., "Stanford study", "Nobel prize discovery")
8. **transformation** - Change narrative (e.g., "one simple change", "before/after secret")

## Database Tables

### premises
- **id:** UUID (auto-generated)
- **premise_type:** TEXT NOT NULL (one of 8 types)
- **name:** TEXT NOT NULL (5-8 words, localized)
- **description:** TEXT (English, for internal use)
- **origin_story:** TEXT (localized, 2-3 sentences)
- **mechanism_claim:** TEXT (why this works)
- **source:** TEXT (default: 'llm_generated')
- **status:** TEXT (default: 'emerging')
- **vertical:** TEXT
- **geo:** TEXT
- **UNIQUE:** (name, vertical)

### event_log
- Emits `PremiseGenerated` event for each new premise

## RPC Function

Created migration: `add_get_underexplored_premise_type_function`

```sql
genomai.get_underexplored_premise_type()
```
Returns the premise_type with the fewest existing premises.

## Response Format

### Success (HTTP 200)
```json
{
  "success": true,
  "created_count": 2,
  "skipped_count": 1,
  "created_ids": ["uuid1", "uuid2"],
  "created_premises": [
    {"id": "uuid1", "name": "...", "premise_type": "method"},
    {"id": "uuid2", "name": "...", "premise_type": "method"}
  ],
  "skipped_premises": ["Duplicate Name"]
}
```

### Error (HTTP 500)
```json
{
  "success": false,
  "error": "Failed to parse LLM response",
  "details": "..."
}
```

## Edge Cases

1. **No winning premises for context:** Continues with empty context in LLM prompt
2. **LLM returns invalid JSON:** Attempts regex extraction, returns error if still fails
3. **All premises are duplicates:** Returns success with empty created_ids array
4. **RPC function fails:** Falls back to counting premises from raw query

## Deployment Notes

1. Workflow file: `infrastructure/workflows/premise_generator.json`
2. Requires manual import to n8n UI or API update
3. After import, activate the workflow in n8n UI
4. Webhook will be registered on first activation

## Credentials Required

- **Supabase API:** `RNItSRYOCypd9H1a`
- **OpenAI API:** `yJNmL2SdGLcPFXuY`

## Testing

```bash
# Test via webhook
curl -X POST https://kazamaqwe.app.n8n.cloud/webhook/premise-generator \
  -H "Content-Type: application/json" \
  -d '{"premise_type": "transformation", "vertical": "nutra", "geo": "RU", "count": 1}'

# Verify in database
SELECT * FROM genomai.premises
WHERE source = 'llm_generated'
ORDER BY created_at DESC LIMIT 5;

# Check events
SELECT * FROM genomai.event_log
WHERE event_type = 'PremiseGenerated'
ORDER BY occurred_at DESC LIMIT 5;
```

## Known Issues

- Schedule Trigger requires manual activation in n8n UI (cannot be activated via API)
- Webhook path must be unique across all workflows
