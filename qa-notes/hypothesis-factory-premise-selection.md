# QA Notes: Hypothesis Factory Premise Selection

**Issue:** #173
**Date:** 2025-12-31
**Status:** Verified & Closed

## What Was Tested

Hypothesis Factory workflow (`oxG1DqxtkTGCqLZi`) premise selection feature:

1. **Select Premise node** - loads active premises from `genomai.premises`
2. **Prompt Assembly** - includes premise context (type, name, origin_story, mechanism_claim)
3. **Persist Hypotheses** - saves `premise_id` to hypothesis record

## Test Execution

```
Workflow: hypothesis_factory_generate (oxG1DqxtkTGCqLZi)
Trigger: POST webhook with idea_id + decision_id + decision=approve
Result: SUCCESS (7793ms)
```

### Test Data Created

```sql
-- Premises (3 records with status='active')
INSERT INTO genomai.premises (premise_type, name, status, vertical) VALUES
  ('secret', 'Tibetan Monks Secret', 'active', 'health'),
  ('discovery', 'Hollywood Elite Method', 'active', 'health'),
  ('breakthrough', 'Suppressed Stanford Study', 'active', 'supplements');

-- Event log with creative_id for approved idea
INSERT INTO genomai.event_log (event_type, entity_type, entity_id, payload, idempotency_key)
VALUES ('IdeaRegistered', 'idea', '8bb6cd0d-ab17-45fc-97eb-b441ca6d0688',
        '{"source": "test", "creative_id": "cf85839f-edbf-488d-a355-8aa5edf40381"}',
        'test_idea_registered_173');
```

### Result Verification

```sql
SELECT h.id, h.premise_id, p.name, p.premise_type
FROM genomai.hypotheses h
JOIN genomai.premises p ON h.premise_id = p.id
WHERE h.id = 'ef95307d-b2aa-4621-8f0e-89366fd4a477';
-- Result: premise_id = 1acd0972-bb6c-4ce9-b340-22dd72bdc581
--         premise_name = "Suppressed Stanford Study"
--         premise_type = "breakthrough"
```

## Edge Cases & Gotchas

### 1. Decision case sensitivity
- Database stores `APPROVE` (uppercase)
- Workflow checks `decision == 'approve'` (lowercase)
- Parse Webhook normalizes: `decision.toLowerCase()`

### 2. Premise table constraints
```sql
CHECK (premise_type IN ('method','discovery','confession','secret','ingredient','mechanism','breakthrough','transformation'))
```

### 3. Empty premises table
- If no active premises, `randomPremise = null`
- Workflow continues without premise context
- hypothesis.premise_id = null (valid behavior)

### 4. event_log is append-only
- Cannot UPDATE event_log records
- Must INSERT new record with corrected payload

## Implementation Notes

- **Supabase node** used instead of HTTP Request to `/premise/select` API
- Simpler architecture, no additional API latency
- Random premise selection happens in Prompt Assembly Code node

## Dependencies

- #171 (main.py update) - CLOSED
- `genomai.premises` table must exist
- Supabase credentials configured
