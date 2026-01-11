# Issue #294: Telegram /drift Command - Drift Detection

## Summary
Added `/drift` command for detecting performance drift in components by comparing baseline vs current win rates using Chi-squared statistical test.

## Implementation

### New Files
- `src/services/drift_detection.py` - Core drift detection logic
- `migrations/032_component_learning_snapshots.sql` - Daily snapshots table

### Database Changes
- New table: `genomai.component_learning_snapshots`
- New function: `genomai.create_component_learning_snapshot()`

### Algorithm
1. **Drift Score**: `|current - baseline| / baseline` (relative change)
2. **Statistical Test**: Chi-squared test with Yates correction
   - p < 0.01 → high confidence
   - p < 0.05 → medium confidence
3. **Severity Levels**:
   - High: >50% drift + p < 0.05
   - Medium: 25-50% drift + p < 0.05
   - Low: <25% or not significant

### Telegram Command
```
/drift              - All components with medium+ drift
/drift emotion_primary - Filter by component type
```

## Testing

### Pre-deployment
- [x] Syntax validation: `python3 -m py_compile`
- [x] Migration applied: table + function created
- [x] Initial snapshot created from component_learnings

### Data Verification
```sql
-- Snapshots created
SELECT COUNT(*) FROM genomai.component_learning_snapshots;  -- 14 rows

-- Sample data
SELECT component_type, component_value, win_rate, sample_size
FROM genomai.component_learning_snapshots
LIMIT 5;
```

### Post-deployment
- [ ] `/drift` responds in Telegram
- [ ] No errors in logs

## Notes
- Drift detection requires historical data to be meaningful
- Daily snapshots should be created by MaintenanceWorkflow
- Currently baseline = current (same day snapshot), so no drift detected yet

## Future Improvements
- Add snapshot creation to MaintenanceWorkflow schedule
- Add automatic alerting when high drift detected
- Implement inline buttons: [Pause Now] [Ignore] [Deep Dive]
