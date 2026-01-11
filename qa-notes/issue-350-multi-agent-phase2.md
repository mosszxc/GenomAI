# QA Notes: Issue #350 - Multi-Agent Orchestration Phase 2

## Summary
Implemented centralized Supabase task queue for multi-agent coordination.

## Changes

### Database
- **Table:** `genomai.agent_tasks` - centralized task queue
- **Functions:**
  - `claim_agent_task(issue_number, agent_id)` - atomic claim
  - `heartbeat_agent_task(issue_number, agent_id)` - keepalive
  - `complete_agent_task(issue_number, agent_id)` - mark done
  - `release_orphaned_tasks(timeout_minutes)` - orphan detection

### Scripts
- `agent-claim.sh` - claim task from queue
- `agent-heartbeat.sh` - send heartbeat
- `agent-complete.sh` - mark task completed
- `agent-add-task.sh` - add task to queue

### Temporal Integration
- `release_orphaned_agent_tasks` activity added to `MaintenanceWorkflow`
- Runs every 6 hours (with existing maintenance schedule)
- Default timeout: 10 minutes without heartbeat

## Test Results

| Test | Result |
|------|--------|
| Table creation | PASS |
| claim_agent_task (success) | PASS - returns true |
| claim_agent_task (double claim) | PASS - returns false |
| heartbeat_agent_task | PASS |
| complete_agent_task | PASS |
| release_orphaned_tasks | PASS - status=abandoned, claimed_by=null |

## SQL Verification
```sql
-- Verify table
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = 'agent_tasks';

-- Test functions
SELECT genomai.claim_agent_task(123, 'agent-id');
SELECT genomai.heartbeat_agent_task(123, 'agent-id');
SELECT genomai.complete_agent_task(123, 'agent-id');
SELECT genomai.release_orphaned_tasks(10);
```

## Migration
`infrastructure/migrations/035_agent_tasks.sql`

## Dependencies
- Phase 1 (#339) - file-based locks (still used for local coordination)
- Phase 2 adds Supabase queue for distributed coordination
