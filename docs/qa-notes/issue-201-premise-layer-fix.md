# QA Notes: Issue #201 - Premise Layer Fix

## Issue
**bug: Premise Layer not operational - 0 premises in database despite closed issues #166-174**

## Investigation

### Initial Claim vs Reality
| Claim | Reality |
|-------|---------|
| 0 premises | 3 premises existed |
| premise_generator INACTIVE | Correct, but not critical |
| Hypothesis Factory broken | Working (100% with premise_id) |

### Root Cause
The issue was based on stale/incorrect data. Premises existed but weren't discovered during initial investigation.

## Actions Taken

1. **Verified existing premises**: 3 active premises found
2. **Added seed premises**: 8 new premises from migration 021
3. **Updated premise_generator workflow**: Refreshed configuration
4. **Closed issue**: With detailed resolution comment

## Final State

| Metric | Before | After |
|--------|--------|-------|
| Active premises | 3 | 11 |
| premise_learnings | 0 | 0 (expected) |
| Hypotheses with premise | 100% | 100% |

## Edge Cases / Gotchas

1. **premise_generator requires examples**: Workflow needs `premise_learnings` with `sample_size >= 5` to generate new premises. Without learning data, it returns error.

2. **Supabase MCP timeouts**: During investigation, Supabase MCP showed "Needs authentication" but worked after retry. May be transient issue.

3. **Seed data in migration**: Migration 021 has `ON CONFLICT DO NOTHING` - if premises with same name exist, they won't be duplicated.

## Verification Commands

```sql
-- Check premises count
SELECT status, COUNT(*) FROM genomai.premises GROUP BY status;

-- Check hypothesis-premise linkage
SELECT COUNT(*) as total, COUNT(premise_id) as with_premise
FROM genomai.hypotheses
WHERE created_at > now() - interval '7 days';
```

## Related Issues
- #166-174: Original Premise Layer implementation (closed)
- #198: Hypothesis Factory (may reference)
