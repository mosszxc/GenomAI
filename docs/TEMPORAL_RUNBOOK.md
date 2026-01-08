# Temporal Operations Runbook

## Quick Reference

| Task | Command |
|------|---------|
| Start workers | `python -m temporal.worker` |
| Create schedules | `python -m temporal.schedules create` |
| List schedules | `python -m temporal.schedules list` |
| Trigger schedule | `python -m temporal.schedules trigger <id>` |
| Check logs | Temporal Cloud UI → Workflows |

## Worker Deployment

### Local Development

```bash
cd decision-engine-service

# Set environment variables
export TEMPORAL_ADDRESS="your-namespace.tmprl.cloud:7233"
export TEMPORAL_NAMESPACE="genomai.xxxxx"
export TEMPORAL_API_KEY="your-api-key"
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="xxx"

# Start workers
python -m temporal.worker
```

### Production (Render)

Workers run as part of the main FastAPI service on Render.
Deploy by pushing to main branch.

```bash
# Check deploy status
render status

# View logs
render logs genomai-decision-engine
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "temporal.worker"]
```

## Schedule Management

### Create All Schedules

```bash
python -m temporal.schedules create
```

Output:
```
Creating all schedules...
Created schedule: keitaro-poller
Created schedule: metrics-processor
Created schedule: learning-loop
Created schedule: daily-recommendations
Created schedule: maintenance
Created 5/5 schedules
```

### List Schedules

```bash
python -m temporal.schedules list
```

### Pause Schedule

```bash
python -m temporal.schedules pause keitaro-poller
```

### Resume Schedule

```bash
python -m temporal.schedules resume keitaro-poller
```

### Trigger Immediately

```bash
python -m temporal.schedules trigger daily-recommendations
```

### Delete All Schedules

```bash
python -m temporal.schedules delete
```

## Monitoring

### Temporal Cloud UI

1. Go to https://cloud.temporal.io
2. Select namespace: `genomai.xxxxx`
3. View:
   - **Workflows** — Running/completed workflows
   - **Schedules** — Scheduled workflows
   - **Task Queues** — Worker status

### Key Metrics

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Workflow failure rate | > 5% | Check logs, restart workers |
| Activity timeout rate | > 10% | Check external APIs |
| Schedule lag | > 1 hour | Check workers running |
| Worker count | < 1 | Deploy more workers |

### Health Checks

```bash
# Check worker connectivity
curl http://localhost:10000/health

# Check Temporal connectivity (via API)
python -c "
import asyncio
from temporal.client import get_temporal_client
async def check():
    client = await get_temporal_client()
    print('Connected to Temporal')
asyncio.run(check())
"
```

## Troubleshooting

### Workflow Not Running

**Symptoms:** Workflow stuck in "Running" state

**Steps:**
1. Check worker logs for errors
2. Verify worker is connected to correct task queue
3. Check activity timeouts
4. Manually terminate if stuck: Temporal UI → Workflow → Terminate

### Activity Timeout

**Symptoms:** Activity times out repeatedly

**Steps:**
1. Check external API status (AssemblyAI, OpenAI, Keitaro)
2. Check Supabase connectivity
3. Increase timeout in activity options
4. Check rate limits

### Schedule Not Triggering

**Symptoms:** Schedule shows "no recent actions"

**Steps:**
1. Verify schedule is not paused: `python -m temporal.schedules list`
2. Resume if paused: `python -m temporal.schedules resume <id>`
3. Check worker is running on correct task queue
4. Trigger manually: `python -m temporal.schedules trigger <id>`

### Worker Crash

**Symptoms:** Worker stops unexpectedly

**Steps:**
1. Check logs for exceptions
2. Check memory usage (OOM?)
3. Restart worker: `python -m temporal.worker`
4. Deploy more workers for redundancy

### Database Connection Issues

**Symptoms:** Activities fail with Supabase errors

**Steps:**
1. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
2. Check Supabase dashboard for issues
3. Check network connectivity
4. Retry workflow

## Common Operations

### Start Failed Workflow

```python
import asyncio
from temporal.client import get_temporal_client
from temporal.workflows import CreativePipelineWorkflow

async def start():
    client = await get_temporal_client()
    handle = await client.start_workflow(
        CreativePipelineWorkflow.run,
        {"creative_id": "xxx", "video_url": "https://..."},
        id="creative-pipeline-xxx",
        task_queue="creative-pipeline",
    )
    result = await handle.result()
    print(result)

asyncio.run(start())
```

### Query Workflow State

```python
import asyncio
from temporal.client import get_temporal_client

async def query():
    client = await get_temporal_client()
    handle = client.get_workflow_handle("workflow-id-xxx")

    # Get workflow result (blocks until complete)
    result = await handle.result()

    # Or just describe
    desc = await handle.describe()
    print(desc.status)

asyncio.run(query())
```

### Terminate Stuck Workflow

```python
import asyncio
from temporal.client import get_temporal_client

async def terminate():
    client = await get_temporal_client()
    handle = client.get_workflow_handle("workflow-id-xxx")
    await handle.terminate("Manual termination - stuck workflow")

asyncio.run(terminate())
```

### Rerun Failed Activity

Temporal automatically retries activities based on retry policy.
To manually restart a workflow from the beginning:

1. Temporal UI → Workflows → Select workflow
2. Click "Reset" or "Restart"

## Emergency Procedures

### All Workflows Failing

1. **Immediate:** Pause all schedules
   ```bash
   python -m temporal.schedules pause keitaro-poller
   python -m temporal.schedules pause metrics-processor
   python -m temporal.schedules pause learning-loop
   python -m temporal.schedules pause daily-recommendations
   python -m temporal.schedules pause maintenance
   ```

2. **Investigate:** Check worker logs, external API status

3. **Fix:** Deploy fix or restart workers

4. **Resume:** Unpause schedules
   ```bash
   python -m temporal.schedules resume keitaro-poller
   # etc.
   ```

### Database Corruption

1. Stop all workflows (pause schedules)
2. Fix database issues via Supabase dashboard
3. Verify data integrity
4. Resume schedules

### External API Down

1. Workflows will retry automatically
2. If persistent, pause affected schedules
3. Wait for API recovery
4. Resume schedules

## Backup & Recovery

### Workflow History

Temporal Cloud retains workflow history for 30 days by default.
No additional backup needed.

### Schedule Configuration

Schedules are defined in code: `temporal/schedules.py`
Version controlled in git.

### Database Backup

Supabase handles database backups automatically.
Point-in-time recovery available.

## Contacts

- **Temporal Cloud Support:** support@temporal.io
- **Supabase Support:** support@supabase.io
- **Project Maintainer:** See CLAUDE.md

## See Also

- [TEMPORAL_WORKFLOWS.md](./TEMPORAL_WORKFLOWS.md) — Workflow reference
- [Temporal Documentation](https://docs.temporal.io/)
- [Temporal Cloud Console](https://cloud.temporal.io/)
