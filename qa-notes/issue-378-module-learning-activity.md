# QA Notes: Issue #378 - Module Learning Activity

## Summary
Added Temporal activities for updating module statistics based on creative test outcomes.

## Changes
- Created `temporal/activities/module_learning.py`:
  - `update_module_stats`: Update individual module stats (win_count, sample_size, spend, revenue)
  - `update_compatibility_stats`: Update compatibility for module pairs
  - `process_module_learning`: Batch process all modules from a creative
- Registered activities in `__init__.py`

## Schema Awareness
Generated columns (DO NOT update directly):
- `module_bank.win_rate` = win_count / sample_size
- `module_bank.avg_roi` = (total_revenue - total_spend) / total_spend
- `module_compatibility.compatibility_score` = win_count / sample_size

## Testing
### Import Test
```
python3 -c "from temporal.activities.module_learning import update_module_stats, update_compatibility_stats, process_module_learning; print('Import OK')"
```
Result: PASSED

### Pre-commit Hooks
- ruff lint: PASSED
- ruff format: PASSED
- critical tests (hashing parity): PASSED
- all unit tests: PASSED

### Production Test
Activities are designed to be called from workflows. Full integration test will be done when module learning workflow (#379+) is implemented.

Activities verified:
1. Import check passes
2. Dataclass definitions correct
3. Generated columns not updated directly
4. Consistent module pair ordering (sorted UUIDs)

## Notes
- Part of Modular Creative System (depends on #375 migration)
- Activities split spend/revenue evenly across modules
- Compatibility pairs use consistent ordering (smaller UUID first)
