# QA Notes: Issue #351 - Multi-Agent Orchestration Phase 3

## Summary
Implemented Temporal-based supervisor pattern for multi-agent task distribution.

## Changes

### Database
- **Table:** `genomai.agents` - agent registry
- **Column added:** `genomai.agent_tasks.labels` (JSONB) - for smart assignment
- **Functions:**
  - `register_agent(agent_id, hostname, specializations, capabilities)` - register/re-register agent
  - `unregister_agent(agent_id)` - mark agent offline
  - `agent_heartbeat(agent_id)` - update heartbeat
  - `get_available_agents(specialization)` - find available agents
  - `assign_task_to_agent(issue_number, specialization)` - smart assignment
  - `release_agent(agent_id)` - release from task
  - `release_orphaned_agents(timeout_minutes)` - orphan detection

### Temporal Workflow
- **Workflow:** `AgentSupervisorWorkflow`
- **Queue:** `agent-supervisor`
- **Schedule:** Every 5 minutes
- **Flow:**
  1. Poll GitHub for pending issues (optional)
  2. Add issues to task queue
  3. Get available agents
  4. Assign tasks using smart assignment (specialization matching)
  5. Release orphaned agents

### Scripts
- `agent-register.sh` - register agent with specializations
- `agent-unregister.sh` - mark agent offline

### Files Changed
| File | Change |
|------|--------|
| `infrastructure/migrations/036_agents_registry.sql` | New migration |
| `decision-engine-service/temporal/workflows/agent_supervisor.py` | New workflow |
| `decision-engine-service/temporal/activities/agent_supervisor.py` | New activities |
| `decision-engine-service/temporal/config.py` | Added TASK_QUEUE_AGENT_SUPERVISOR |
| `decision-engine-service/temporal/worker.py` | Added agent_supervisor_worker |
| `decision-engine-service/temporal/schedules.py` | Added agent-supervisor schedule |
| `scripts/agent-register.sh` | New script |
| `scripts/agent-unregister.sh` | New script |

## Test Results

| Test | Result |
|------|--------|
| Table creation | PASS |
| register_agent | PASS - returns true, agent status = online |
| get_available_agents | PASS - returns registered agents |
| unregister_agent | PASS - agent status = offline |
| labels column in agent_tasks | PASS |

## SQL Verification
```sql
-- Verify table
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = 'agents';

-- Test registration
SELECT genomai.register_agent('my-agent', 'hostname', '["temporal"]'::jsonb, '{}'::jsonb);

-- Get available agents
SELECT * FROM genomai.get_available_agents();
SELECT * FROM genomai.get_available_agents('temporal');

-- Unregister
SELECT genomai.unregister_agent('my-agent');
```

## Usage

### Agent Registration
```bash
# Register agent with specializations
./scripts/agent-register.sh temporal migration

# Send heartbeats (use agent-heartbeat.sh from Phase 2)
./scripts/agent-heartbeat.sh

# Unregister when done
./scripts/agent-unregister.sh
```

### Temporal Schedule
```bash
# Create schedule
python -m temporal.schedules create

# Trigger manually
python -m temporal.schedules trigger agent-supervisor

# List schedules
python -m temporal.schedules list
```

## Smart Assignment Logic
1. Find agents with matching specialization first
2. If no match, use any available agent
3. Priority by most recent heartbeat
4. Atomic claim using `FOR UPDATE SKIP LOCKED`

## Dependencies
- Phase 1 (#339) - file-based locks
- Phase 2 (#350) - Supabase task queue, claim_agent_task function
