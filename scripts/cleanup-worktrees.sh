#!/bin/bash
# Cleanup merged worktrees and branches (with TTL support)
# Usage: ./scripts/cleanup-worktrees.sh [--dry-run] [--force] [--ttl DAYS]

set -e

DRY_RUN=""
FORCE_CLEAN=""
TTL_DAYS=7  # Default: keep worktrees for 7 days after merge

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-n)
            DRY_RUN="true"
            shift
            ;;
        --force|-f)
            FORCE_CLEAN="true"
            shift
            ;;
        --ttl)
            TTL_DAYS="$2"
            shift 2
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
[ "$FORCE_CLEAN" = "true" ] && echo "(force mode - ignoring TTL)"
echo "TTL: $TTL_DAYS days"
echo ""

# Fetch latest from remote
git fetch --prune --quiet

# Get list of merged branches (excluding main)
MERGED=$(git branch --merged main | grep -v '^\*' | grep -v 'main' | sed 's/^[+ ]*//' || true)

CLEANED=0
PRESERVED=0

# Helper: check if worktree is older than TTL
is_expired() {
    local worktree_path="$1"
    local merged_at_file="$worktree_path/.merged-at"

    # If no .merged-at file, check directory mtime
    if [ ! -f "$merged_at_file" ]; then
        # No merge marker - use directory modification time
        local dir_age_days
        if [[ "$OSTYPE" == "darwin"* ]]; then
            dir_age_days=$(( ( $(date +%s) - $(stat -f %m "$worktree_path") ) / 86400 ))
        else
            dir_age_days=$(( ( $(date +%s) - $(stat -c %Y "$worktree_path") ) / 86400 ))
        fi
        [ "$dir_age_days" -ge "$TTL_DAYS" ]
        return $?
    fi

    # Parse .merged-at timestamp
    local merged_at=$(cat "$merged_at_file")
    local merged_ts
    if [[ "$OSTYPE" == "darwin"* ]]; then
        merged_ts=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$merged_at" +%s 2>/dev/null || echo 0)
    else
        merged_ts=$(date -d "$merged_at" +%s 2>/dev/null || echo 0)
    fi

    local now_ts=$(date +%s)
    local age_days=$(( (now_ts - merged_ts) / 86400 ))

    [ "$age_days" -ge "$TTL_DAYS" ]
}

for branch in $MERGED; do
    [ -z "$branch" ] && continue

    # Check if it's a worktree
    WORKTREE_PATH=$(git worktree list | grep "\[$branch\]" | awk '{print $1}' || true)

    if [ -n "$WORKTREE_PATH" ]; then
        # Check TTL unless --force
        if [ "$FORCE_CLEAN" != "true" ] && ! is_expired "$WORKTREE_PATH"; then
            # Preserved - skip both worktree and branch
            if [ -f "$WORKTREE_PATH/.merged-at" ]; then
                echo "  Preserved: $branch (merged: $(cat "$WORKTREE_PATH/.merged-at"))"
            else
                echo "  Preserved: $branch (no merge marker)"
            fi
            ((PRESERVED++)) || true
            continue
        fi

        echo "Expired: $branch"
        echo "  Worktree: $WORKTREE_PATH"
        if [ "$DRY_RUN" != "true" ]; then
            git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || true
        fi
        ((CLEANED++)) || true
    fi

    # Delete branch (only if worktree was removed or didn't exist)
    echo "  Branch: $branch (deleting)"
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
        # Use -F for fixed string matching (handles unicode/cyrillic paths)
        if ! git worktree list | grep -qF "$dirname"; then
            # Orphaned directory - but still respect TTL!
            # Don't delete active work just because git lost track of it
            if [ "$FORCE_CLEAN" != "true" ] && ! is_expired "$dir"; then
                echo "  Orphaned (preserved - TTL not expired): $dirname"
                ((PRESERVED++)) || true
                continue
            fi
            echo "  Orphaned (expired): $dirname"
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
    echo "Preserved (TTL not expired): $PRESERVED items"
    echo "Run without --dry-run to apply"
else
    echo "Cleaned: $CLEANED items"
    echo "Preserved: $PRESERVED items"
fi
echo ""
echo "Options:"
echo "  --force    Clean all merged worktrees (ignore TTL)"
echo "  --ttl N    Set TTL to N days (default: 7)"

echo ""
echo "Current worktrees:"
git worktree list
