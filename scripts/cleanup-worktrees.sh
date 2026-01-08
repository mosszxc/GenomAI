#!/bin/bash
# Cleanup merged worktrees and branches
# Usage: ./scripts/cleanup-worktrees.sh [--dry-run] [--all]

set -e

DRY_RUN=""
CLEAN_ALL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-n)
            DRY_RUN="true"
            shift
            ;;
        --all|-a)
            CLEAN_ALL="true"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

echo "=== Cleaning up merged worktrees ==="
[ "$DRY_RUN" = "true" ] && echo "(dry-run mode - no changes will be made)"
echo ""

# Fetch latest from remote
git fetch --prune --quiet

# Get list of merged branches (excluding main)
MERGED=$(git branch --merged main | grep -v '^\*' | grep -v 'main' | sed 's/^[+ ]*//' || true)

CLEANED=0

for branch in $MERGED; do
    [ -z "$branch" ] && continue

    # Check if it's a worktree
    WORKTREE_PATH=$(git worktree list | grep "\[$branch\]" | awk '{print $1}' || true)

    if [ -n "$WORKTREE_PATH" ]; then
        echo "Worktree: $WORKTREE_PATH"
        if [ "$DRY_RUN" != "true" ]; then
            git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || true
        fi
        ((CLEANED++)) || true
    fi

    echo "  Branch: $branch (merged)"
    if [ "$DRY_RUN" != "true" ]; then
        git branch -d "$branch" 2>/dev/null || true

        # Delete remote if exists
        if git ls-remote --heads origin "$branch" 2>/dev/null | grep -q "$branch"; then
            echo "  Remote: origin/$branch"
            git push origin --delete "$branch" 2>/dev/null || true
        fi
    fi
done

# Clean up orphaned directories in .worktrees/
if [ -d "$WORKTREES_DIR" ]; then
    echo ""
    echo "Checking .worktrees/ for orphaned directories..."

    for dir in "$WORKTREES_DIR"/*/; do
        [ ! -d "$dir" ] && continue
        dirname=$(basename "$dir")

        # Check if this worktree is still registered
        if ! git worktree list | grep -q "$dir"; then
            echo "  Orphaned: $dirname"
            if [ "$DRY_RUN" != "true" ]; then
                rm -rf "$dir"
            fi
            ((CLEANED++)) || true
        fi
    done
fi

# Prune stale worktree references
if [ "$DRY_RUN" != "true" ]; then
    git worktree prune
fi

echo ""
echo "=== Summary ==="
if [ "$DRY_RUN" = "true" ]; then
    echo "Would clean: $CLEANED items"
    echo "Run without --dry-run to apply"
else
    echo "Cleaned: $CLEANED items"
fi

echo ""
echo "Current worktrees:"
git worktree list
