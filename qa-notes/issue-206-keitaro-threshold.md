# Issue #206: Keitaro Poller metrics 11h stale

## Problem

E2E test Phase 2C.1 was flagging Keitaro metrics as stale after 2 hours, but Keitaro Poller workflow runs only once daily at midnight.

## Root Cause

Mismatch between:
- **E2E threshold**: 2 hours (inherited from old assumption of 30-min polling)
- **Actual schedule**: Once daily at 00:00

## Fix

Updated `.claude/commands/e2e.md`:
- Phase 2C.1 criteria: `staleness < interval '25 hours'`
- Severity levels: WARNING > 25h, ERROR > 48h
- Thresholds table updated accordingly

## Verification

```sql
SELECT MAX(updated_at), now() - MAX(updated_at) as staleness
FROM genomai.raw_metrics_current;
-- Result: staleness ~10h = OK for daily polling
```

## Notes

- Keitaro Poller workflow ID: `0TrVJOtHiNEEAsTN`
- Last successful run: 2026-01-04 00:00 (as expected)
- Using 25h instead of 24h to allow for minor schedule drift
