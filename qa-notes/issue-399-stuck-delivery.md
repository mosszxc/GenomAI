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
-- 3 rows, all retry_count=0
```

### Post-fix Verification
- Deploy: live (dep-d5hs7m49c44c73dot340)
- Buyer has telegram_id: 999999999
- Hypotheses will be picked up by next MaintenanceWorkflow run (every 6h)

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
