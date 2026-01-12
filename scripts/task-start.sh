#!/bin/bash
# Start working on a GitHub issue in a separate worktree
# Usage: ./scripts/task-start.sh <issue-number>

set -e

ISSUE_NUM="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number>"
    echo ""
    echo "Available issues:"
    gh issue list --state open --limit 10
    exit 1
fi

# Get issue info
ISSUE_TITLE=$(gh issue view "$ISSUE_NUM" --json title -q '.title')
if [ -z "$ISSUE_TITLE" ]; then
    echo "Error: Issue #$ISSUE_NUM not found"
    exit 1
fi

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

# Mark issue as in-progress
echo ""
echo "=== Updating issue status ==="
gh issue edit "$ISSUE_NUM" --add-label "status:in-progress" --remove-label "status:ready" 2>/dev/null || true
echo "Issue #$ISSUE_NUM marked as in-progress"

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
