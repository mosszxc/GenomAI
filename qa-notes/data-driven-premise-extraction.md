# Data-Driven Premise Extraction

## Summary
Implemented data-driven premise generation system that extracts premise patterns from concluded creatives based on real Keitaro metrics (ROI) and transcript analysis.

## Changes

### 1. Seed Premises Deactivated
- All 19 seed premises status changed from `active` to `emerging`
- Verified: `SELECT status, COUNT(*) FROM genomai.premises GROUP BY status`

### 2. New Temporal Activities (`temporal/activities/premise_extraction.py`)
- `load_creative_data()` - Loads creative + decomposed + transcript + metrics
- `extract_premises_via_llm()` - GPT-4o extracts premise patterns from creative data
- `upsert_premise_and_learning()` - Creates/updates premises and learnings
- `emit_premise_extraction_event()` - Observability event logging

### 3. New Temporal Workflows (`temporal/workflows/premise_extraction.py`)
- `PremiseExtractionWorkflow` - Processes single creative
- `BatchPremiseExtractionWorkflow` - Batch processing for multiple creatives

### 4. Conclusion Mechanism (`temporal/activities/maintenance.py`)
- `conclude_creatives_and_get_ids()` - New activity that:
  - Finds creatives ready for conclusion (spend >= threshold, days >= min)
  - Sets `test_result` based on ROI (win if ROI > 0, loss otherwise)
  - Sets `concluded_at` timestamp
  - Returns list of concluded creative IDs

### 5. MaintenanceWorkflow Integration
- Added Step 10: Premise Extraction
- Automatically triggers after concluding creatives
- Runs BatchPremiseExtractionWorkflow for all concluded creatives

### 6. Worker Registration
- Both workflows registered in metrics_worker
- All activities registered

## Key Design Decisions

### Win/Loss Determination
- `test_result = 'win'` if ROI > 0
- `test_result = 'loss'` if ROI <= 0
- Threshold: min_spend >= $50, min_days >= 3

### Both Wins AND Losses Are Valuable
- Winning creatives: Extract successful premise patterns
- Losing creatives: Extract anti-patterns (marked with `is_negative=true`)
- Both contribute to `premise_learnings` table

### Premise Extraction Flow
```
Concluded Creative
    ↓
load_creative_data (decomposed + transcript + metrics)
    ↓
extract_premises_via_llm (GPT-4o analysis)
    ↓
upsert_premise_and_learning (create/update in DB)
    ↓
emit_premise_extraction_event (observability)
```

## Testing Notes
- Currently no creatives in DB to test with
- Will activate when Keitaro data flows in
- Monitor: `SELECT * FROM genomai.premises WHERE source = 'data_extracted'`

## Trigger Points
1. **Automatic (MaintenanceWorkflow)**: Every 6 hours, checks for concluded creatives
2. **Manual**: Can trigger `BatchPremiseExtractionWorkflow` with list of creative IDs

## Files Modified
| File | Action |
|------|--------|
| `temporal/activities/premise_extraction.py` | CREATED |
| `temporal/workflows/premise_extraction.py` | CREATED |
| `temporal/activities/maintenance.py` | ADDED conclude_creatives_and_get_ids |
| `temporal/workflows/maintenance.py` | ADDED premise extraction step |
| `temporal/worker.py` | REGISTERED workflows and activities |

## Verification Queries
```sql
-- Check seed premises deactivated
SELECT status, COUNT(*) FROM genomai.premises GROUP BY status;

-- Monitor new premises
SELECT * FROM genomai.premises
WHERE source = 'data_extracted'
ORDER BY created_at DESC LIMIT 10;

-- Check premise learnings
SELECT pl.*, p.name
FROM genomai.premise_learnings pl
JOIN genomai.premises p ON p.id = pl.premise_id
ORDER BY pl.updated_at DESC LIMIT 10;

-- Monitor concluded creatives
SELECT id, test_result, concluded_at
FROM genomai.creatives
WHERE test_result IS NOT NULL
ORDER BY concluded_at DESC LIMIT 10;
```
