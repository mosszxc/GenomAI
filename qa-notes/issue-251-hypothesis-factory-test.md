# Issue #251: Hypothesis Factory Process Test

## Summary
Тестирование и исправление процесса hypothesis-factory.

## Bug Found & Fixed
**Problem:** `variables` column was always NULL in `genomai.hypotheses` table.

**Root Cause:**
- `save_hypotheses` activity не принимал параметр `variables`
- Workflow не передавал `decomposition_payload` при сохранении

**Fix:**
1. Added `variables: Optional[dict] = None` parameter to `save_hypotheses` activity
2. Pass `decomposition_payload` from workflow to activity
3. Bump `PROMPT_VERSION` to v4

## Files Changed
- `decision-engine-service/temporal/activities/hypothesis_generation.py`
- `decision-engine-service/temporal/workflows/creative_pipeline.py`

## Validation Results

### Before Fix (v3)
```sql
SELECT prompt_version, COUNT(*), SUM(CASE WHEN variables IS NOT NULL THEN 1 ELSE 0 END) as with_variables
FROM genomai.hypotheses GROUP BY prompt_version;
-- v3: 19 records, 0 with variables
```

### After Fix (v4)
Next pipeline run will create hypotheses with variables populated.

## Test Commands
```bash
# Health check
curl https://genomai.onrender.com/health

# Check hypotheses with variables
SELECT h.id, h.prompt_version, h.variables IS NOT NULL as has_variables
FROM genomai.hypotheses h ORDER BY created_at DESC LIMIT 5;
```

## Gotchas
1. API `/api/decision/` requires Bearer token authorization
2. Full e2e test requires actual video URL to trigger CreativePipelineWorkflow
3. Telegram delivery only happens if buyer_id is set

## Commit
`ab28be3` - fix(hypothesis): pass variables from decomposed_creatives to hypotheses
