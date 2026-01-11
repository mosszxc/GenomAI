# QA Notes: Issue #399 - Stuck Hypothesis Delivery

## Problem
E2E test detected 3 hypotheses stuck on delivery for >5 minutes with:
- `status=pending`
- `retry_count=0`
- `last_error=null`

## Root Causes Found

### 1. Wrong Column Name in telegram.py
`get_buyer_chat_id()` queried non-existent column `telegram_chat_id`:
```python
# BEFORE (broken)
f"{rest_url}/buyers?id=eq.{buyer_id}&select=telegram_chat_id"
return data[0].get("telegram_chat_id")

# AFTER (fixed)
f"{rest_url}/buyers?id=eq.{buyer_id}&select=telegram_id"
return data[0].get("telegram_id")
```

### 2. Retry Mechanism Ignored Pending Hypotheses
`retry_failed_hypotheses()` only processed `status=failed`, not stuck `pending`:
```python
# BEFORE
f"?status=eq.failed"

# AFTER
f"?or=(status.eq.failed,and(status.eq.pending,created_at.lt.{stuck_cutoff_iso}))"
```

### 3. Workflow Design Issue (not fixed)
CreativePipelineWorkflow sends only the first hypothesis (line 382), leaving others in `pending` forever.
This is a design limitation, now mitigated by the retry mechanism.

## Files Changed
- `decision-engine-service/temporal/activities/telegram.py` - column name fix
- `decision-engine-service/temporal/activities/hygiene_cleanup.py` - added pending to retry query

## Test Results

### Pre-fix State
```sql
SELECT id, status, retry_count FROM genomai.hypotheses WHERE status='pending';
-- 3 rows, all retry_count=0, last_retry_at=null
```

### Post-fix Production Test
```bash
curl -X POST "https://genomai.onrender.com/api/schedules/maintenance/trigger" \
  -H "X-API-Key: $API_KEY"
# {"success":true,"message":"Schedule 'maintenance' triggered successfully"}
```

### Results After MaintenanceWorkflow
| Field | Before | After |
|-------|--------|-------|
| retry_count | 0 | 1 |
| last_retry_at | null | 2026-01-11 15:47:54 |
| last_error | null | "Bad Request: chat not found" |

**Verdict:** PASSED
- `retry_failed_hypotheses` picked up stuck pending hypotheses ✓
- `get_buyer_chat_id` correctly fetched `telegram_id` column ✓
- Telegram API was called (error is expected for test buyer with fake chat_id 999999999) ✓

## Test Command
```bash
# Check stuck hypotheses
SELECT h.id, h.status, h.buyer_id, b.telegram_id
FROM genomai.hypotheses h
LEFT JOIN genomai.buyers b ON h.buyer_id = b.id
WHERE h.status = 'pending'
  AND h.created_at < now() - interval '5 minutes';
```

## PR
https://github.com/mosszxc/GenomAI/pull/403
