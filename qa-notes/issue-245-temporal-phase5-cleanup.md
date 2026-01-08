# Issue #245: feat(temporal): Phase 5 - Cleanup & n8n Deprecation

## Summary
Final phase of n8n → Temporal migration. Migrated remaining workflows:
- Daily Recommendation Generator → DailyRecommendationWorkflow
- Recommendation Delivery → SingleRecommendationDeliveryWorkflow
- Pipeline Health Monitor → MaintenanceWorkflow

## Files Created
| File | Purpose |
|------|---------|
| `temporal/workflows/recommendation.py` | Daily recommendation generation workflow |
| `temporal/activities/recommendation.py` | Activities for recommendation system |
| `temporal/workflows/maintenance.py` | Periodic maintenance workflow |
| `temporal/activities/maintenance.py` | Activities for cleanup and integrity |
| `docs/TEMPORAL_WORKFLOWS.md` | Complete workflow reference |
| `docs/TEMPORAL_RUNBOOK.md` | Operational runbook |
| `infrastructure/n8n-archive/README.md` | Archive of deprecated n8n workflows |

## Key Decisions

### 1. Cron vs Interval for Daily Schedule
**Decision:** Used cron expression `0 9 * * *` for daily recommendations
**Reason:** More precise timing at 09:00 UTC daily vs interval drift

### 2. MaintenanceWorkflow Instead of Health Monitor
**Decision:** Created lightweight maintenance workflow
**Reason:** Temporal has built-in monitoring. MaintenanceWorkflow handles:
- Reset stale buyer states (> 6h)
- Expire old recommendations (> 7 days)
- Data integrity checks

### 3. keep_alive_decision_engine Deleted
**Decision:** Marked as DELETED, not migrated
**Reason:** Temporal workers are persistent, no keep-alive needed

## Schedules

| Schedule ID | Workflow | Interval/Cron |
|-------------|----------|---------------|
| `keitaro-poller` | KeitaroPollerWorkflow | 10 min |
| `metrics-processor` | MetricsProcessingWorkflow | 30 min |
| `learning-loop` | LearningLoopWorkflow | 1 hour |
| `daily-recommendations` | DailyRecommendationWorkflow | 09:00 UTC |
| `maintenance` | MaintenanceWorkflow | 6 hours |

## Test Commands

```bash
# Start workers locally
cd decision-engine-service && python -m temporal.worker

# Create all schedules
cd decision-engine-service && python -m temporal.schedules create

# List schedules
cd decision-engine-service && python -m temporal.schedules list

# Trigger schedule manually
cd decision-engine-service && python -m temporal.schedules trigger daily-recommendations
```

## Gotchas

1. **cron_expressions is a list** - ScheduleSpec expects `cron_expressions=["0 9 * * *"]` not string
2. **Activity timeouts** - Recommendation activities have 5min timeout for LLM calls
3. **Skip existing** - DailyRecommendationWorkflow checks for existing daily recommendation to avoid duplicates

## n8n Cleanup

### Archived (not deleted from n8n Cloud yet)
- 6 legacy workflows moved to `infrastructure/n8n-archive/`
- n8n Cloud account kept for 30-day rollback safety

### Deleted
- `ClXUPP2IvWRgu99y` keep_alive_decision_engine - not needed

## Post-Migration Checklist
- [x] All workflows migrated
- [x] Schedules configured
- [x] Documentation updated
- [x] CLAUDE.md updated (n8n → Temporal)
- [ ] Workers deployed to production (after PR merge)
- [ ] Schedules created on Temporal Cloud (after deploy)
- [ ] n8n Cloud account cancelled (after 30 days)
