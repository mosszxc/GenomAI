# QA Notes: Issue #372 - Add profit_confirmed metric

## Changes
- Added `profit_confirmed` field to `KeitaroMetrics` dataclass
- Updated API payloads in `get_tracker_metrics` and `get_batch_metrics`
- Updated response parsing in both activities
- Field included in `to_dict()` for automatic JSONB storage

## Files Changed
- `decision-engine-service/temporal/activities/keitaro.py`

## Testing Done
- [x] Syntax verification: `python3 -c "from temporal.activities.keitaro import KeitaroMetrics; m = KeitaroMetrics('test', '2025-01-01', profit_confirmed=100.0); print(m.to_dict())"`
- [x] Unit tests: 85 passed

## Post-Deploy Verification
```bash
# Trigger workflow
python -m temporal.schedules trigger keitaro-poller

# Verify in Supabase
SELECT tracker_id, metrics->>'profit_confirmed' as profit_confirmed
FROM genomai.raw_metrics_current
ORDER BY updated_at DESC LIMIT 5;
```

## Notes
- No DB migration needed (JSONB column)
- No workflow changes needed (uses `to_dict()`)
- Keitaro API metric name: `profit_confirmed`
