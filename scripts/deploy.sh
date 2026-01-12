#!/bin/bash
# Deploy: merge develop → main → Render auto-deploy
# Usage: ./scripts/deploy.sh [--major|--minor|--patch]
# Default: --patch

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

# Parse version bump type
BUMP_TYPE="${1:---patch}"
case "$BUMP_TYPE" in
    --major) BUMP="major" ;;
    --minor) BUMP="minor" ;;
    --patch|*) BUMP="patch" ;;
esac

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

# Get current version from tag or default
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
CURRENT_VERSION="${CURRENT_VERSION#v}"  # Remove 'v' prefix

# Parse version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
MAJOR="${MAJOR:-0}"
MINOR="${MINOR:-0}"
PATCH="${PATCH:-0}"

# Bump version
case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"

echo ""
echo "Version: $CURRENT_VERSION → $NEW_VERSION ($BUMP)"

# Collect changes for changelog
echo ""
echo "=== Changes in this release ==="

# Get closed issues from commits
ISSUES=$(git log main..origin/develop --oneline | grep -oE '#[0-9]+' | sort -u | tr '\n' ' ')
echo "Issues: ${ISSUES:-none}"

# Get commit summary
COMMITS=$(git log main..origin/develop --oneline --no-merges)
echo ""
echo "Commits:"
echo "$COMMITS" | head -20

# Generate changelog entry
CHANGELOG_FILE="$PROJECT_ROOT/CHANGELOG.md"
DATE=$(date +%Y-%m-%d)

CHANGELOG_ENTRY="## [$NEW_VERSION] - $DATE

### Changes
$(git log main..origin/develop --oneline --no-merges | sed 's/^/- /')

### Issues
$(echo "$ISSUES" | tr ' ' '\n' | grep -v '^$' | sed 's/^/- Closes /' || echo "- No issues")

---

"

# Prepend to changelog
if [ -f "$CHANGELOG_FILE" ]; then
    echo "$CHANGELOG_ENTRY$(cat "$CHANGELOG_FILE")" > "$CHANGELOG_FILE"
else
    echo "# Changelog

$CHANGELOG_ENTRY" > "$CHANGELOG_FILE"
fi

echo ""
echo "✓ CHANGELOG.md updated"

# Merge develop into main
git merge origin/develop --no-edit

# Commit changelog
git add CHANGELOG.md
git commit -m "release: $NEW_VERSION" --no-verify || true

# Create tag
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION"

# Push to trigger Render deploy
git push origin main --tags

# Create GitHub Release with changelog
echo ""
echo "Creating GitHub Release..."

RELEASE_NOTES="## Changes

$(git log main~$COMMITS_AHEAD..main --oneline --no-merges | grep -v "^.* release:" | sed 's/^/- /')

## Issues
$(echo "$ISSUES" | tr ' ' '\n' | grep -v '^$' | sed 's/^/- Closes /' || echo "- No issues closed")
"

gh release create "$NEW_VERSION" \
    --title "$NEW_VERSION" \
    --notes "$RELEASE_NOTES" \
    --latest

echo ""
echo "=== Deploy started ==="
echo "Version: $NEW_VERSION"
echo "Render will auto-deploy in ~3 minutes."
echo ""
echo "GitHub Release: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/releases/tag/$NEW_VERSION"
echo "Render status:  https://dashboard.render.com/web/srv-d54vf524d50c739kc2m0"
