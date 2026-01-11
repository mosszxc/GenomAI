# Active Agents

Shared status board for multi-agent coordination. All Claude Code agents update this file.

## Active Tasks

| Issue | Agent | Status | Branch | Started |
|-------|-------|--------|--------|---------|
<!-- Entries are added/removed by task-start.sh and task-done.sh -->

## Rules

1. **Before starting task:** Check if issue is already claimed
2. **After task-start.sh:** Add row to table above
3. **After task-done.sh:** Remove row from table

## Lock Files

Lock files are stored in `.agents/locks/` directory. They are auto-generated and should not be edited manually.

```bash
# Check active locks
ls .agents/locks/

# Lock format: issue-{N}.lock
# Content: JSON with agent info, timestamp
```
