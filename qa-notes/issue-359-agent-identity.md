# QA Notes: Issue #359 - Agent Identity Commands

## Summary
Added commands `/ag1`-`/ag5` for terminal identification and `/next` for getting tasks from queue.

## Changes

### Commands Added
| Command | Purpose |
|---------|---------|
| `/ag1` - `/ag5` | Set agent identity (writes to ~/.claude-agent-id) |
| `/next` | Get and claim next task from Supabase queue |

### Scripts
- **agent-next.sh** (new) — Claims next pending task from queue
- **agent-register.sh** (updated) — Reads ID from file
- **agent-claim.sh** (updated) — Reads ID from file
- **agent-heartbeat.sh** (updated) — Reads ID from file
- **agent-complete.sh** (updated) — Reads ID from file

### ID Resolution Logic
```bash
if [ -f ~/.claude-agent-id ]; then
    AGENT_ID=$(cat ~/.claude-agent-id)
else
    AGENT_ID="${HOSTNAME:-$(hostname)}-$$"
fi
```

## Test Commands
```bash
# Set identity
/ag1

# Verify
cat ~/.claude-agent-id
# → agent-1

# Add task to queue
./scripts/agent-add-task.sh 100

# Get next task
/next
# → "Взял issue #100, начинаю работу..."
```

## Files Changed
| File | Action |
|------|--------|
| `.claude/commands/ag1.md` | Created |
| `.claude/commands/ag2.md` | Created |
| `.claude/commands/ag3.md` | Created |
| `.claude/commands/ag4.md` | Created |
| `.claude/commands/ag5.md` | Created |
| `.claude/commands/next.md` | Created |
| `scripts/agent-next.sh` | Created |
| `scripts/agent-register.sh` | Modified |
| `scripts/agent-claim.sh` | Modified |
| `scripts/agent-heartbeat.sh` | Modified |
| `scripts/agent-complete.sh` | Modified |

## Integration
Works with existing AgentSupervisorWorkflow from Phase 3 (#351).
