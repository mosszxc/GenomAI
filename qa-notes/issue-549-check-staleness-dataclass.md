# Issue #549: Replace unsafe args unpacking in check_staleness

## Problem
In `maintenance.py` workflow, `check_staleness` activity was called with positional args:
```python
args=[None, None]  # What are these arguments?
```

This is unsafe because if activity signature changes, code will silently pass wrong values.

## Solution
1. Created `CheckStalenessInput` dataclass in `temporal/activities/maintenance.py`
2. Updated `check_staleness` activity to accept single dataclass argument
3. Updated workflow call to use `CheckStalenessInput()` instead of `args=[None, None]`

## Changes
- `decision-engine-service/temporal/activities/maintenance.py`: Added `CheckStalenessInput` dataclass, updated activity signature
- `decision-engine-service/temporal/workflows/maintenance.py`: Import dataclass, use it in activity call

## Test
```bash
cd decision-engine-service && python3 -c "from temporal.activities.maintenance import CheckStalenessInput; print('OK: CheckStalenessInput imported')" && python3 -c "from temporal.workflows.maintenance import MaintenanceWorkflow; print('OK: MaintenanceWorkflow imported')"
```
