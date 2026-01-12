#!/bin/bash
# Deploy: merge develop → main → Render auto-deploy
# Usage: ./scripts/deploy.sh

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

echo "=== Deploy: develop → main ==="

# Ensure we're on main and up to date
git checkout main
git pull origin main

# Check develop exists and has commits ahead
git fetch origin develop
COMMITS_AHEAD=$(git rev-list --count main..origin/develop 2>/dev/null || echo "0")

if [ "$COMMITS_AHEAD" = "0" ]; then
    echo "Nothing to deploy. develop is up to date with main."
    exit 0
fi

echo "Deploying $COMMITS_AHEAD commit(s) from develop..."

# Merge develop into main
git merge origin/develop --no-edit

# Push to trigger Render deploy
git push origin main

echo ""
echo "=== Deploy started ==="
echo "Render will auto-deploy in ~3 minutes."
echo ""
echo "Check status:"
echo "  https://dashboard.render.com/web/srv-d54vf524d50c739kc2m0"
