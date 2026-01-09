# Issue #272: Event Table Name Bug

## Problem
All Temporal activities used incorrect table name `events` instead of `event_log`.
Also used incorrect field names:
- `source` (doesn't exist in schema)
- `created_at` (should be `occurred_at`)

## Root Cause
Copy-paste error when migrating from n8n to Temporal. Original code assumed `events` table existed.

## Files Fixed
1. `temporal/activities/recommendation.py:401` - emit_recommendation_event()
2. `temporal/activities/supabase.py:341` - emit_event()
3. `temporal/activities/maintenance.py:269` - emit_maintenance_event()
4. `temporal/activities/telegram.py:264` - hypothesis delivery event

## Schema Reference
```sql
genomai.event_log:
- id: uuid NOT NULL
- event_type: text NOT NULL
- entity_type: text
- entity_id: uuid
- payload: jsonb
- occurred_at: timestamp NOT NULL
- idempotency_key: text
```

## Test
```sql
INSERT INTO genomai.event_log (id, event_type, entity_type, payload, occurred_at)
VALUES (gen_random_uuid(), 'TestEvent', 'test', '{"test": true}'::jsonb, NOW());
```

## PR
https://github.com/mosszxc/GenomAI/pull/273
