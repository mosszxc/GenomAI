# Issue #308: Hygiene Agent

## Summary
Implemented comprehensive hygiene system for GenomAI with:
- Data cleanup (expired/orphan records)
- Health monitoring (connections, table sizes, pending counts)
- Telegram alerts to admin

## Components Created

### New Files
| File | Purpose |
|------|---------|
| `temporal/workflows/health_check.py` | HealthCheckWorkflow (every 3h) |
| `temporal/activities/hygiene_cleanup.py` | Cleanup activities |
| `temporal/activities/hygiene_health.py` | Health check activities + alerts |
| `temporal/models/hygiene.py` | Dataclasses for Input/Result |
| `infrastructure/migrations/031_hygiene_reports.sql` | Reports table |

### Modified Files
| File | Changes |
|------|---------|
| `temporal/workflows/maintenance.py` | +cleanup step, +cleanup_stats |
| `temporal/worker.py` | +HealthCheckWorkflow, +hygiene activities |
| `temporal/schedules.py` | +health-check schedule |
| `temporal/models/__init__.py` | +hygiene model exports |

## Cleanup Operations (MaintenanceWorkflow)
| Data | Retention | Activity |
|------|-----------|----------|
| historical_import_queue (expired) | 7 days | cleanup_expired_import_queue |
| knowledge_extractions (rejected) | 30 days | cleanup_rejected_knowledge |
| raw_metrics_current (orphan) | immediate | cleanup_orphan_raw_metrics |
| buyer_states (idle) | 30 days | cleanup_idle_buyer_states |
| staleness_snapshots | 90 days | archive_staleness_snapshots |

## Health Checks (HealthCheckWorkflow)
- Supabase connection + latency
- Table sizes (8 monitored tables)
- Pending counts (4 queue tables)
- Health score computation (0.0-1.0)
- Telegram alerts on threshold breach

## Schedules
| Schedule | Interval |
|----------|----------|
| maintenance | 6 hours |
| health-check | 3 hours |

## Telegram Alerts
- Admin: mosszxc (telegram_id: 291678304)
- Severity levels: CRITICAL, WARNING, INFO
- Bot: UniAIHelper_bot (via TELEGRAM_BOT_TOKEN)

## Testing
```bash
# Create health-check schedule
python -m temporal.schedules create

# Trigger manually
python -m temporal.schedules trigger health-check

# Check results
SELECT * FROM genomai.hygiene_reports ORDER BY created_at DESC LIMIT 5;
```

## Verification Checklist
- [x] Migration applied (031_hygiene_reports)
- [x] Schedule created (health-check)
- [x] Workflow executed successfully
- [x] Report saved to hygiene_reports (2 records, health_score: 0.88)
- [x] Alert threshold logic verified (no alert at score 0.88 > 0.8 threshold)

## Verification Results (2026-01-11)
```
hygiene_reports: 2 records
- health_score: 0.88
- supabase_connected: true
- supabase_latency_ms: ~253ms
- alerts_sent: 0 (score above threshold)
```
