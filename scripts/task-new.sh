#!/bin/bash
# Create issue + worktree + open Cursor in one command
# Usage: ./scripts/task-new.sh "Task title" ["Description"]

set -e

TITLE="$1"
DESCRIPTION="${2:-}"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if [ -z "$TITLE" ]; then
    echo "Usage: $0 \"Task title\" [\"Description\"]"
    exit 1
fi

echo "=== Creating task ==="
echo "Title: $TITLE"

# Detect if bug or feature
if echo "$TITLE" | grep -qiE "(fix|bug|crash|error|broken|не работает|сломал|ошибка)"; then
    LABEL="bug"
else
    LABEL="enhancement"
fi

# Create issue
if [ -n "$DESCRIPTION" ]; then
    ISSUE_URL=$(gh issue create --title "$TITLE" --body "$DESCRIPTION" --label "$LABEL" --label "status:ready")
else
    ISSUE_URL=$(gh issue create --title "$TITLE" --body "Created via task-new" --label "$LABEL" --label "status:ready")
fi

# Extract issue number from URL
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')

echo "Issue created: #$ISSUE_NUM"
echo "Label: $LABEL"

# Create worktree
"$PROJECT_ROOT/scripts/task-start.sh" "$ISSUE_NUM"

# Find worktree path
WORKTREE_PATH=$(find "$WORKTREES_DIR" -maxdepth 1 -type d -name "issue-${ISSUE_NUM}-*" 2>/dev/null | head -1)

# Open in Cursor
if [ -n "$WORKTREE_PATH" ]; then
    echo ""
    echo "Opening in Cursor..."
    cursor "$WORKTREE_PATH"
fi

echo ""
echo "=== Ready to work ==="
echo "Issue: $ISSUE_URL"
echo "Worktree: $WORKTREE_PATH"
