#!/bin/bash
# Finish task: create PR, merge, cleanup worktree
# Usage: ./scripts/task-done.sh <issue-number> [--no-pr]

set -e

ISSUE_NUM="$1"
NO_PR="$2"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number> [--no-pr]"
    echo ""
    echo "Active worktrees:"
    git worktree list
    exit 1
fi

# Find the worktree for this issue
WORKTREE_PATH=$(find "$WORKTREES_DIR" -maxdepth 1 -type d -name "issue-${ISSUE_NUM}-*" 2>/dev/null | head -1)

if [ -z "$WORKTREE_PATH" ] || [ ! -d "$WORKTREE_PATH" ]; then
    echo "Error: No worktree found for issue #$ISSUE_NUM"
    echo "Looking for: $WORKTREES_DIR/issue-${ISSUE_NUM}-*"
    exit 1
fi

# Get branch name
BRANCH_NAME=$(basename "$WORKTREE_PATH")

echo "=== Finishing task ==="
echo "Issue: #$ISSUE_NUM"
echo "Branch: $BRANCH_NAME"
echo "Worktree: $WORKTREE_PATH"

# Check for uncommitted changes in worktree
cd "$WORKTREE_PATH"
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "Warning: Uncommitted changes in worktree"
    git status --short
    echo ""
    read -p "Commit all changes? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add -A
        git commit -m "feat: complete issue #$ISSUE_NUM"
    else
        echo "Aborting. Commit your changes first."
        exit 1
    fi
fi

# Push branch
echo ""
echo "Pushing branch..."
git push -u origin "$BRANCH_NAME"

# Create PR if not --no-pr
if [ "$NO_PR" != "--no-pr" ]; then
    echo ""
    echo "Creating PR..."
    PR_URL=$(gh pr create --title "Closes #$ISSUE_NUM" --body "Closes #$ISSUE_NUM" --head "$BRANCH_NAME" 2>/dev/null || echo "")

    if [ -n "$PR_URL" ]; then
        echo "PR created: $PR_URL"
        echo ""
        read -p "Merge PR now? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            gh pr merge "$BRANCH_NAME" --squash --delete-branch
            echo "PR merged!"
        fi
    else
        echo "PR already exists or couldn't be created"
        gh pr view "$BRANCH_NAME" --web 2>/dev/null || true
    fi
fi

# Return to main project
cd "$PROJECT_ROOT"

# Cleanup worktree
echo ""
echo "Cleaning up worktree..."
git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || true
git branch -d "$BRANCH_NAME" 2>/dev/null || true

# Fetch and prune
git fetch --prune
git worktree prune

echo ""
echo "=== Done ==="
echo "Task #$ISSUE_NUM completed"
