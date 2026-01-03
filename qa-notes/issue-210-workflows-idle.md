# Issue #210: All n8n workflows idle 24h+

## Summary
Workflows were reported as idle for 24+ hours. Investigation showed they are actually working, just processing limited data.

## Root Cause
- Not a bug - workflows work correctly
- Limited data to process (only 1 buyer with keitaro_source, 9 creatives in "pending" status)
- Schedule triggers running normally

## Evidence
- `raw_metrics_current`: 3 records, last updated 2026-01-03 15:49:26
- `event_log`: 93 RawMetricsObserved events total
- `daily_metrics_snapshot`: snapshot created 2026-01-03 15:41:19
- 9 events in last hour

## Key Queries
```sql
-- Check workflow activity
SELECT event_type, COUNT(*), MAX(occurred_at)
FROM genomai.event_log
WHERE occurred_at > NOW() - INTERVAL '6 hours'
GROUP BY event_type;

-- Check metrics freshness
SELECT tracker_id, date, updated_at, NOW() - updated_at as age
FROM genomai.raw_metrics_current
ORDER BY updated_at DESC LIMIT 5;
```

## Verification Method
1. Check Supabase API logs for n8n activity (User-Agent: axios/1.12.0, n8n)
2. Query event_log for recent events
3. Check raw_metrics_current for data freshness

## Gotchas
- n8n API tools unavailable (missing N8N_API_KEY in MCP config)
- Use Supabase logs + event_log as alternative verification
- Webhook endpoints may return 404 if workflow not active in UI

## Resolution
Closed as working correctly. Workflows execute on schedule, limited output due to limited input data.
