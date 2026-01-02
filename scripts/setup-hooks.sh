#!/bin/bash
# Install git hooks for this repository

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Create post-merge hook
cat > "$REPO_ROOT/.git/hooks/post-merge" << 'EOF'
#!/bin/bash
# After git pull/merge - cleanup merged worktrees

if [ -x "./scripts/cleanup-worktrees.sh" ]; then
    echo "🧹 Running worktree cleanup..."
    ./scripts/cleanup-worktrees.sh
fi
EOF

chmod +x "$REPO_ROOT/.git/hooks/post-merge"
echo "✅ Installed post-merge hook"
