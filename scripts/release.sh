#!/bin/bash
# Merge develop -> main для релиза
# Usage: ./scripts/release.sh [--dry-run]
#
# Создаёт PR из develop в main. После merge Render автоматически задеплоит.

set -e

DRY_RUN=""
if [ "$1" == "--dry-run" ]; then
    DRY_RUN="true"
    echo "DRY RUN MODE - no changes will be made"
    echo ""
fi

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "=== GenomAI Release ==="
echo ""

# Проверка что мы в main репозитории (не в worktree)
if [[ "$PROJECT_ROOT" == *".worktrees"* ]]; then
    echo "Error: Run this from main repository, not worktree"
    exit 1
fi

# Проверка uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Uncommitted changes detected"
    git status --short
    exit 1
fi

# Проверить что ветка develop существует
if ! git show-ref --verify --quiet refs/heads/develop && ! git show-ref --verify --quiet refs/remotes/origin/develop; then
    echo "Error: Branch 'develop' does not exist"
    echo ""
    echo "Create it first:"
    echo "  git checkout -b develop"
    echo "  git push -u origin develop"
    exit 1
fi

# Fetch latest
echo "Fetching latest changes..."
git fetch origin main develop

# Показать что будет смержено
echo ""
echo "=== Changes to be released ==="
git log --oneline origin/main..origin/develop 2>/dev/null || git log --oneline main..develop
echo ""

COMMIT_COUNT=$(git rev-list --count origin/main..origin/develop 2>/dev/null || git rev-list --count main..develop)
echo "Total commits: $COMMIT_COUNT"

if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo "No changes to release. develop is up to date with main."
    exit 0
fi

# Подтверждение
if [ "$DRY_RUN" != "true" ]; then
    echo ""
    read -p "Proceed with release? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Release cancelled."
        exit 0
    fi
fi

# Выполнение release
if [ "$DRY_RUN" != "true" ]; then
    echo ""
    echo "Creating release PR..."

    # Получить список коммитов для body
    COMMITS=$(git log --oneline origin/main..origin/develop 2>/dev/null || git log --oneline main..develop)

    # Создать PR develop -> main
    PR_URL=$(gh pr create \
        --title "Release: merge develop to main" \
        --body "$(cat <<EOF
## Release Summary

Merging $COMMIT_COUNT commits from develop to main.

### Commits included:
$COMMITS

### Checklist
- [ ] All tests pass
- [ ] Changes reviewed
- [ ] Ready for production

---
After merge, Render will automatically deploy to production.
EOF
)" \
        --base main \
        --head develop \
        --label "release" \
        2>/dev/null || echo "")

    if [ -n "$PR_URL" ]; then
        echo "Release PR created: $PR_URL"
        echo ""
        echo "Next steps:"
        echo "1. Review the PR"
        echo "2. Ensure all checks pass"
        echo "3. Merge when ready (this will trigger deploy)"
    else
        echo "PR already exists or couldn't be created"
        echo "Check existing PRs: gh pr list --base main --head develop"
        gh pr view develop --web 2>/dev/null || true
    fi
else
    echo ""
    echo "[DRY RUN] Would create PR: develop -> main"
    echo "[DRY RUN] Commits: $COMMIT_COUNT"
fi

echo ""
echo "=== Release process initiated ==="
