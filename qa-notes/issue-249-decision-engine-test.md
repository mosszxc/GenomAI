# Issue #249: Decision Engine Test

## Test Date
2026-01-08

## Test Summary
Decision Engine API validated successfully.

## Test Commands

```bash
# Health check
curl -s "https://genomai.onrender.com/health"
# Response: {"status":"ok","timestamp":"2026-01-08T14:05:49.787548"}

# Decision request
curl -s -X POST "https://genomai.onrender.com/api/decision/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {API_KEY}" \
  -d '{"idea_id": "86ce27f1-8f81-4e2c-95fd-916cae445928"}'
```

## Results

### API Response
```json
{
  "success": true,
  "decision": {
    "decision_id": "64fee00c-6825-46f0-a3b3-ef70db9ea050",
    "decision_type": "approve",
    "passed_checks": ["schema_validity", "death_memory", "fatigue_constraint", "risk_budget"]
  }
}
```

### DB Verification
- `genomai.decisions`: Record created with decision=approve
- `genomai.decision_traces`: 4 checks recorded, all PASSED

## Checks Detail
| Check | Result | Details |
|-------|--------|---------|
| schema_validity | PASSED | - |
| death_memory | PASSED | - |
| fatigue_constraint | PASSED | MVP stub: "not implemented" |
| risk_budget | PASSED | 3/100 active ideas, 97 slots remaining |

## Edge Cases Discovered
1. `fatigue_constraint` is a stub - needs implementation
2. All 12 decisions in DB are approvals - no reject/defer test cases exist
3. API requires Bearer token in Authorization header

## Gotchas
- API_KEY is application key, not Render API key (rnd_...)
- Free tier Render may return 503 if service is sleeping
- Schema uses `decision` column not `decision_type`

## Recommendations
1. Create test idea that triggers REJECT (e.g., with death_state set)
2. Create test idea that triggers DEFER (e.g., exceed risk_budget)
3. Implement fatigue_constraint check
