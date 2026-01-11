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

# Set terminal title
printf '\033]0;Issue #%s\007' "$ISSUE_NUM"

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
    # Create new branch and worktree from main
    git fetch origin main
    git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" origin/main
fi

echo ""
echo "=== Ready ==="
echo "Worktree created at: $WORKTREE_PATH"
echo ""
echo "To work in this worktree:"
echo "  cd $WORKTREE_PATH"
echo ""
echo "Or open in Cursor:"
echo "  cursor $WORKTREE_PATH"
echo ""
echo "When done, run:"
echo "  ./scripts/task-done.sh $ISSUE_NUM"
