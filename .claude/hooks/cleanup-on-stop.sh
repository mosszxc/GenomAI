#!/bin/bash
# Runs after Claude session ends - cleanup merged worktrees

cd "$(dirname "$0")/../.." || exit 0

# Only run if script exists
if [ -x "./scripts/cleanup-worktrees.sh" ]; then
    ./scripts/cleanup-worktrees.sh 2>/dev/null || true
fi
