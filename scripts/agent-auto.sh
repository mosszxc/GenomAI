#!/bin/bash
# Autonomous bug-fixing agent (single agent, no coordination needed)
# Usage: ./scripts/agent-auto.sh [--max-tasks N] [--dry-run] [--skip-tests]
#
# Requires:
#   - make up (FastAPI + Temporal running) — unless --skip-tests
#   - GitHub CLI authenticated
#
# Labels:
#   - Required: bug + agent-ready
#   - Excluded: human-only, agent-failed, needs-discussion

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

# Parse arguments
MAX_TASKS="${MAX_TASKS:-999}"
DRY_RUN=""
SKIP_TESTS=""
IDLE_DELAY=60

while [[ $# -gt 0 ]]; do
    case $1 in
        --max-tasks)
            MAX_TASKS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS="--skip-tests"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Graceful shutdown
CURRENT_ISSUE=""
cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -n "$CURRENT_ISSUE" ]; then
        echo "Releasing issue #$CURRENT_ISSUE"
        gh issue edit "$CURRENT_ISSUE" --remove-label "status:in-progress" 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "=== Agent Auto Started ==="
echo "Max tasks: $MAX_TASKS"
echo "Dry run: ${DRY_RUN:-false}"
echo "Skip tests: ${SKIP_TESTS:-false}"
echo "Press Ctrl+C to stop"
echo ""

COMPLETED=0
FAILED=0
MAX_FAILED=3  # Stop after 3 consecutive failures

while [ "$COMPLETED" -lt "$MAX_TASKS" ] && [ "$FAILED" -lt "$MAX_FAILED" ]; do
    echo "--- Looking for next issue ---"

    # Get issue with required labels and select first suitable one
    SELECTED=$(gh issue list \
        --state open \
        --label "bug" \
        --label "agent-ready" \
        --json number,title,labels \
        -L 20 2>/dev/null | python3 -c "
import sys, json

try:
    issues = json.load(sys.stdin)
except:
    issues = []

for issue in issues:
    num = issue['number']
    title = issue['title']
    labels = [l['name'] for l in issue.get('labels', [])]

    # Skip if has excluded labels
    excluded = {'human-only', 'agent-failed', 'needs-discussion', 'status:in-progress'}
    if excluded & set(labels):
        continue

    # Return first valid issue
    print(f'{num}|{title}')
    break
" || echo "")

    if [ -z "$SELECTED" ]; then
        echo "No suitable issues found. Waiting ${IDLE_DELAY}s..."
        sleep "$IDLE_DELAY"
        continue
    fi

    ISSUE_NUM=$(echo "$SELECTED" | cut -d'|' -f1)
    ISSUE_TITLE=$(echo "$SELECTED" | cut -d'|' -f2-)

    # Skip if already has open PR
    if gh pr list --head "issue-${ISSUE_NUM}-" --state open 2>/dev/null | grep -q .; then
        echo "Issue #$ISSUE_NUM already has PR, skipping..."
        gh issue edit "$ISSUE_NUM" --remove-label "agent-ready" 2>/dev/null || true
        continue
    fi

    # Skip if worktree already exists
    if ls -d "$PROJECT_ROOT/.worktrees/issue-${ISSUE_NUM}-"* 2>/dev/null | grep -q .; then
        echo "Issue #$ISSUE_NUM already has worktree, skipping..."
        continue
    fi

    echo "Selected: #$ISSUE_NUM - $ISSUE_TITLE"
    CURRENT_ISSUE="$ISSUE_NUM"

    if [ "$DRY_RUN" = "true" ]; then
        echo "[DRY RUN] Would process issue #$ISSUE_NUM"
        CURRENT_ISSUE=""
        COMPLETED=$((COMPLETED + 1))
        continue
    fi

    # 1. Create worktree
    echo ""
    echo "=== Step 1: Creating worktree ==="
    if ! ./scripts/task-start.sh "$ISSUE_NUM"; then
        echo "Failed to create worktree, skipping..."
        CURRENT_ISSUE=""
        continue
    fi

    # Find worktree path
    WORKTREE_PATH=$(ls -d "$PROJECT_ROOT/.worktrees/issue-${ISSUE_NUM}-"* 2>/dev/null | head -1)
    if [ -z "$WORKTREE_PATH" ]; then
        echo "Worktree not found, skipping..."
        CURRENT_ISSUE=""
        continue
    fi

    # 2. Solve with Claude Code
    echo ""
    echo "=== Step 2: Solving with Claude ==="
    cd "$WORKTREE_PATH"

    # Run Claude Code with auto-solve skill (no timeout on macOS)
    if claude --print --dangerously-skip-permissions "/auto-solve $ISSUE_NUM"; then
        echo "Claude completed successfully"
    else
        echo "Claude failed or timed out"
        gh issue edit "$ISSUE_NUM" --add-label "agent-failed" 2>/dev/null || true
        gh issue comment "$ISSUE_NUM" --body "Agent failed to solve this issue (timeout or error)" 2>/dev/null || true
        cd "$PROJECT_ROOT"
        CURRENT_ISSUE=""
        FAILED=$((FAILED + 1))
        echo "Failed attempts: $FAILED/$MAX_FAILED"
        continue
    fi

    cd "$PROJECT_ROOT"

    # 3. Complete task (tests + PR + merge)
    echo ""
    echo "=== Step 3: Completing task ==="
    if ./scripts/task-done.sh "$ISSUE_NUM" $SKIP_TESTS; then
        echo ""
        echo "=== Issue #$ISSUE_NUM COMPLETED ==="
        COMPLETED=$((COMPLETED + 1))
        FAILED=0  # Reset on success
        echo "Progress: $COMPLETED/$MAX_TASKS"
    else
        echo "task-done.sh failed"
        gh issue edit "$ISSUE_NUM" --add-label "agent-failed" 2>/dev/null || true
        FAILED=$((FAILED + 1))
        echo "Failed attempts: $FAILED/$MAX_FAILED"
    fi

    CURRENT_ISSUE=""
    echo ""
done

echo ""
echo "=== Agent Auto Finished ==="
echo "Completed: $COMPLETED tasks"
