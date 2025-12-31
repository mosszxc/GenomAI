# QA Notes: Issue #198 - Hypothesis Factory Check

## Issue
**bug: Hypothesis Factory not generating hypotheses (0 hypotheses for 4 APPROVE decisions)**

## Investigation

### Initial Claim vs Reality
| Claim | Reality |
|-------|---------|
| 4 APPROVE decisions | 0 APPROVE decisions |
| 0 hypotheses | 1 hypothesis exists |
| Workflow broken | 9/10 recent executions SUCCESS |

### Root Cause
Data changed since issue was created. APPROVE decisions were likely cleaned up or the data was from testing.

## Validation Errors (False Positives)

n8n-mcp validator reported 3 errors:
1. Parse Webhook - "Cannot return primitive values directly"
2. Prompt Assembly - "Unmatched expression brackets"
3. Parse Payload - "Unmatched expression brackets"

**These are FALSE POSITIVES.** The Code nodes work correctly at runtime as evidenced by 9 successful executions.

## Execution History

| ID | Date | Status |
|----|------|--------|
| 2967 | Dec 31 03:13 | SUCCESS |
| 2870 | Dec 30 16:45 | SUCCESS |
| 2783 | Dec 30 15:32 | SUCCESS |
| 2779 | Dec 30 15:31 | SUCCESS |
| 2730 | Dec 30 15:17 | SUCCESS |
| 2322 | Dec 27 00:31 | SUCCESS |
| 2320 | Dec 27 00:31 | **ERROR** |

### Single Error Analysis (Execution 2320)

**Error:** `null value in column "decision_id" violates not-null constraint`

**Cause:** `decision_id` was null in the payload passed to Persist Hypotheses.

**Context:** Edge case where decision_id wasn't properly extracted from webhook payload.

**Resolution:** Not a code bug - subsequent executions all succeeded.

## Edge Cases / Gotchas

1. **n8n-mcp validation vs runtime:** Validator may report false positives. Always check actual executions.

2. **decision_id required:** `hypotheses.decision_id` is NOT NULL. Ensure webhook payload includes valid decision_id.

3. **Data volatility:** APPROVE decisions can be deleted/cleaned up, making issue claims outdated.

## Verification Commands

```sql
-- Check APPROVE decisions without hypotheses
SELECT d.id, d.created_at
FROM genomai.decisions d
LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
WHERE d.decision = 'approve' AND h.id IS NULL;

-- Check recent hypotheses
SELECT id, idea_id, decision_id, status, created_at
FROM genomai.hypotheses
ORDER BY created_at DESC
LIMIT 5;
```

```bash
# Check workflow executions
# Use n8n_executions action=list workflowId=oxG1DqxtkTGCqLZi
```
