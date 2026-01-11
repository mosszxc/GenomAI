# Issue #334: Integrate Deploy Lock into task-done.sh

## Problem

`task-done.sh` merged PRs without checking for active deploys on Render.

With multiple agents working in parallel, this could cause:
- Deploy queue overflow
- Race conditions during merge

`safe-deploy.sh` existed but wasn't integrated into the main workflow.

## Solution

1. Added `--check-only` flag to `safe-deploy.sh`:
   - Checks deploy status via Render API
   - Waits for active deploy to complete
   - Exits without push (for integration into other scripts)

2. Integrated deploy check into `task-done.sh`:
   - Calls `safe-deploy.sh --check-only` before `gh pr merge`
   - Graceful fallback when `RENDER_API_KEY` not set

## Test Commands

```bash
# Test --check-only flag
export RENDER_API_KEY="rnd_..."
./scripts/safe-deploy.sh --check-only
# Expected: "✓ Deploy check passed"

# Verify integration (dry run)
./scripts/task-done.sh 999 --no-pr
# Expected: deploy check appears before merge prompt
```

## Files Changed

| File | Change |
|------|--------|
| `scripts/safe-deploy.sh` | Added `--check-only` flag |
| `scripts/task-done.sh` | Deploy check before merge |

## Edge Cases

- **RENDER_API_KEY not set**: Warning shown, merge proceeds (backwards compatible)
- **API timeout**: 10 minute max wait, then proceeds
- **API error**: Proceeds with warning
