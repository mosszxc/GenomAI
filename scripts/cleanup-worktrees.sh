#!/bin/bash
# Cleanup merged vibe-kanban worktrees and branches

set -e

echo "=== Cleaning up merged worktrees ==="

# Get list of merged branches (excluding main)
MERGED=$(git branch --merged main | grep -v '^\*' | grep -v 'main' | sed 's/^[+ ]*//')

for branch in $MERGED; do
    # Check if it's a worktree
    WORKTREE_PATH=$(git worktree list | grep "\[$branch\]" | awk '{print $1}')

    if [ -n "$WORKTREE_PATH" ]; then
        echo "Removing worktree: $WORKTREE_PATH"
        git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || true
    fi

    echo "Deleting local branch: $branch"
    git branch -d "$branch" 2>/dev/null || true

    # Delete remote if exists
    if git ls-remote --heads origin "$branch" | grep -q "$branch"; then
        echo "Deleting remote branch: $branch"
        git push origin --delete "$branch" 2>/dev/null || true
    fi
done

# Prune stale worktrees
git worktree prune

echo "=== Done ==="
git worktree list
git branch -a
