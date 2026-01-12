#!/bin/bash
# Finish task: commit, push, create PR to develop
# Usage: ./scripts/task-done.sh <issue-number> [--no-pr] [--skip-tests]

set -e

# Parse arguments
ISSUE_NUM=""
NO_PR=""
SKIP_TESTS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-pr)
            NO_PR="true"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
        *)
            if [ -z "$ISSUE_NUM" ]; then
                ISSUE_NUM="$1"
            fi
            shift
            ;;
    esac
done

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number> [--no-pr] [--skip-tests]"
    echo ""
    echo "Options:"
    echo "  --no-pr       Skip PR creation"
    echo "  --skip-tests  Skip pre-merge tests"
    echo ""
    echo "Active worktrees:"
    git worktree list
    exit 1
fi

# Find the worktree for this issue
WORKTREE_PATH=$(find "$WORKTREES_DIR" -maxdepth 1 -type d -name "issue-${ISSUE_NUM}-*" 2>/dev/null | head -1)

if [ -z "$WORKTREE_PATH" ] || [ ! -d "$WORKTREE_PATH" ]; then
    echo "Error: No worktree found for issue #$ISSUE_NUM"
    exit 1
fi

BRANCH_NAME=$(basename "$WORKTREE_PATH")

echo "=== Finishing task ==="
echo "Issue: #$ISSUE_NUM"
echo "Branch: $BRANCH_NAME"

# Check for uncommitted changes
cd "$WORKTREE_PATH"
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "Committing changes..."
    git add -A
    git commit -m "feat: complete issue #$ISSUE_NUM

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
fi

# Run tests unless skipped
if [ "$SKIP_TESTS" != "true" ]; then
    # Local test first
    echo ""
    echo "Running local test..."
    cd "$PROJECT_ROOT"
    if ! ./scripts/test-local.sh "$ISSUE_NUM"; then
        echo "Local test failed. Fix issues and re-run."
        exit 1
    fi

    # Then unit tests
    echo ""
    echo "Running unit tests (make ci)..."
    if ! make ci; then
        echo "Unit tests failed. Fix issues and re-run."
        exit 1
    fi
    echo "✓ All tests passed"
    cd "$WORKTREE_PATH"
fi

# Check qa-notes exists
QA_NOTE=$(find "$PROJECT_ROOT/qa-notes" -name "*issue-${ISSUE_NUM}*" 2>/dev/null | head -1)
if [ -z "$QA_NOTE" ]; then
    QA_NOTE=$(find "$WORKTREE_PATH/qa-notes" -name "*${ISSUE_NUM}*" 2>/dev/null | head -1)
fi

if [ -z "$QA_NOTE" ]; then
    echo ""
    echo "⚠️  qa-notes/issue-${ISSUE_NUM}-*.md not found"
    echo "Create qa-notes before completing."
    exit 1
fi
echo "✓ qa-notes found: $(basename "$QA_NOTE")"

# Update issue status
echo ""
echo "Updating issue status..."
gh issue edit "$ISSUE_NUM" --add-label "status:pending-deploy" --remove-label "status:in-progress" 2>/dev/null || true

# Push branch
echo ""
echo "Pushing branch..."
git push -u origin "$BRANCH_NAME"

# Create PR to develop
if [ "$NO_PR" != "true" ]; then
    echo ""
    echo "Creating PR to develop..."
    PR_URL=$(gh pr create \
        --title "Closes #$ISSUE_NUM" \
        --body "Closes #$ISSUE_NUM" \
        --head "$BRANCH_NAME" \
        --base develop \
        2>/dev/null || echo "")

    if [ -n "$PR_URL" ]; then
        echo "PR created: $PR_URL"
    else
        echo "PR already exists or couldn't be created"
        gh pr view "$BRANCH_NAME" --web 2>/dev/null || true
    fi
fi

cd "$PROJECT_ROOT"
echo ""
echo "=== Done ==="
echo "PR created to develop branch."
echo "Run ./scripts/deploy.sh when ready to deploy."
