# Issue #346: Failed Hypotheses Missing buyer_id

## Problem
MaintenanceWorkflow found 2 failed hypotheses that couldn't be retried because they were missing `buyer_id`:
- `ef95307d-b2aa-4621-8f0e-89366fd4a477`
- `4358f699-fd49-48d0-8cc1-9f09b5aba941`

## Root Cause
`save_hypotheses` activity in `hypothesis_generation.py` did not include `buyer_id` when creating hypothesis records, even though `buyer_id` was available in the workflow input.

**Code path:**
```
CreativeInput.buyer_id → CreativePipelineWorkflow → save_hypotheses (NOT propagated) → hypotheses table
```

## Fix
1. Added `buyer_id: Optional[str] = None` parameter to `save_hypotheses` activity
2. Updated `CreativePipelineWorkflow` to pass `input.buyer_id` to `save_hypotheses`
3. `buyer_id` is now included in the hypothesis record

## Files Changed
- `decision-engine-service/temporal/activities/hypothesis_generation.py` - Added buyer_id parameter
- `decision-engine-service/temporal/workflows/creative_pipeline.py` - Pass buyer_id to activity

## Testing
- Unit tests: 102 passed
- Affected records: Already deleted from DB (0 records in hypotheses table)

## Related
- KNOWN_ISSUES.md: "Hypothesis Factory Missing buyer_id Propagation" (Issue #222, #226)
- This fix resolves the root cause documented there
