#!/bin/bash
# Start working on a GitHub issue in a separate worktree
# Usage: ./scripts/task-start.sh <issue-number>

set -e

ISSUE_NUM="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"
AGENTS_DIR="$PROJECT_ROOT/.agents"
LOCKS_DIR="$AGENTS_DIR/locks"

# Generate unique agent ID (hostname + terminal session)
AGENT_ID="${HOSTNAME:-$(hostname)}-$$"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number>"
    echo ""
    echo "Available issues:"
    gh issue list --state open --limit 10
    echo ""
    echo "=== Active Agents ==="
    if [ -d "$LOCKS_DIR" ] && [ -n "$(ls -A "$LOCKS_DIR" 2>/dev/null)" ]; then
        for lock in "$LOCKS_DIR"/*.lock; do
            [ -f "$lock" ] || continue
            issue=$(basename "$lock" .lock | sed 's/issue-//')
            agent=$(sed -n 's/.*"agent":[ ]*"\([^"]*\)".*/\1/p' "$lock" 2>/dev/null || echo "unknown")
            started=$(sed -n 's/.*"started_at":[ ]*"\([^"]*\)".*/\1/p' "$lock" 2>/dev/null || echo "unknown")
            echo "  Issue #$issue - Agent: $agent (since $started)"
        done
    else
        echo "  (none)"
    fi
    exit 1
fi

# Get issue info
ISSUE_TITLE=$(gh issue view "$ISSUE_NUM" --json title -q '.title')
if [ -z "$ISSUE_TITLE" ]; then
    echo "Error: Issue #$ISSUE_NUM not found"
    exit 1
fi

# === MULTI-AGENT COORDINATION ===
mkdir -p "$LOCKS_DIR"
LOCK_FILE="$LOCKS_DIR/issue-${ISSUE_NUM}.lock"

# Check if issue is already locked by another agent
if [ -f "$LOCK_FILE" ]; then
    EXISTING_AGENT=$(sed -n 's/.*"agent":[ ]*"\([^"]*\)".*/\1/p' "$LOCK_FILE" 2>/dev/null || echo "unknown")
    LOCKED_AT=$(sed -n 's/.*"started_at":[ ]*"\([^"]*\)".*/\1/p' "$LOCK_FILE" 2>/dev/null || echo "unknown")
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  ISSUE #$ISSUE_NUM IS ALREADY CLAIMED                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Agent: $EXISTING_AGENT"
    echo "  Since: $LOCKED_AT"
    echo ""
    echo "Options:"
    echo "  1. Choose a different issue"
    echo "  2. Coordinate with the other agent"
    echo "  3. Force claim: rm $LOCK_FILE && $0 $ISSUE_NUM"
    echo ""
    exit 1
fi

# Create lock file
LOCK_TMP="$LOCK_FILE.tmp.$$"
cat > "$LOCK_TMP" << EOF
{
  "agent": "$AGENT_ID",
  "issue": $ISSUE_NUM,
  "title": "$ISSUE_TITLE",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
mv "$LOCK_TMP" "$LOCK_FILE"
echo "🔒 Lock acquired for issue #$ISSUE_NUM"

# Create branch name from issue (lowercase, dashes, max 50 chars)
BRANCH_NAME="issue-${ISSUE_NUM}-$(echo "$ISSUE_TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-40)"
WORKTREE_PATH="$WORKTREES_DIR/$BRANCH_NAME"

echo "=== Starting task ==="
echo "Issue: #$ISSUE_NUM - $ISSUE_TITLE"
echo "Branch: $BRANCH_NAME"
echo "Worktree: $WORKTREE_PATH"

# Ensure worktrees directory exists
mkdir -p "$WORKTREES_DIR"

# Check if branch already exists
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    echo "Branch already exists, checking out existing worktree..."
    if [ -d "$WORKTREE_PATH" ]; then
        echo "Worktree already exists at $WORKTREE_PATH"
    else
        git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
    fi
else
    # Create new branch and worktree from develop
    git fetch origin develop
    git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" origin/develop
fi

echo ""
echo "=== Starting local dev server ==="
# Запускаем локальный сервер в фоне
"$PROJECT_ROOT/scripts/local-dev.sh" &
DEV_PID=$!
sleep 5

# Проверяем что сервер запустился
if [ -f /tmp/genomai-dev/server-*.pid ]; then
    PORT=$(basename /tmp/genomai-dev/server-*.pid .pid | sed 's/server-//')
    echo "Local server running on http://localhost:$PORT"
else
    echo "Warning: Server may not have started correctly"
fi

echo ""
echo "=== Ready ==="
echo "Worktree: $WORKTREE_PATH"
echo "Server: http://localhost:$PORT"
echo ""
echo "To work in this worktree:"
echo "  cd $WORKTREE_PATH"
echo ""
echo "Or open in Cursor:"
echo "  cursor $WORKTREE_PATH"
echo ""
echo "When done, run:"
echo "  ./scripts/task-done.sh $ISSUE_NUM"
