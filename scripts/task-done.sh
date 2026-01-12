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

# Check qa-notes exists
QA_NOTE=$(find "$PROJECT_ROOT/qa-notes" -name "*issue-${ISSUE_NUM}*" 2>/dev/null | head -1)
if [ -z "$QA_NOTE" ]; then
    QA_NOTE=$(find "$WORKTREE_PATH/qa-notes" -name "*${ISSUE_NUM}*" 2>/dev/null | head -1)
fi

if [ -z "$QA_NOTE" ]; then
    echo ""
    echo "⚠️  qa-notes/issue-${ISSUE_NUM}-*.md not found"
    echo "Create qa-notes with ## Test section before completing."
    exit 1
fi
echo "✓ qa-notes found: $(basename "$QA_NOTE")"

# Run tests unless skipped
if [ "$SKIP_TESTS" != "true" ]; then
    # Extract and run functional test from qa-notes
    echo ""
    echo "=== Functional Test ==="

    # Extract test command from qa-notes (between ```bash and ``` after ## Test)
    TEST_CMD=$(sed -n '/^## Test/,/^## /p' "$QA_NOTE" | sed -n '/```bash/,/```/p' | grep -v '```' | head -5)

    if [ -z "$TEST_CMD" ]; then
        echo "⚠️  No test command found in qa-notes"
        echo "Add ## Test section with \`\`\`bash block"
        exit 1
    fi

    echo "Command: $TEST_CMD"
    echo ""

    cd "$PROJECT_ROOT"
    if eval "$TEST_CMD"; then
        echo ""
        echo "✓ Functional test passed"
    else
        echo ""
        echo "✗ Functional test failed"
        exit 1
    fi

    # Then unit tests
    echo ""
    echo "=== Unit Tests ==="
    if ! make ci; then
        echo "Unit tests failed. Fix issues and re-run."
        exit 1
    fi
    echo "✓ All tests passed"
    cd "$WORKTREE_PATH"
fi

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

# Merge PR to develop
if [ "$NO_PR" != "true" ] && [ -n "$PR_URL" ]; then
    echo ""
    echo "Merging PR to develop..."
    if gh pr merge "$BRANCH_NAME" --squash --delete-branch 2>/dev/null; then
        echo "✓ PR merged"
    else
        echo "⚠️  Could not auto-merge. Merge manually: $PR_URL"
    fi
fi

# CRITICAL: Verify issue is closed (A014)
echo ""
echo "=== Verifying issue closed ==="
sleep 2  # Give GitHub time to process
ISSUE_STATE=$(gh issue view "$ISSUE_NUM" --json state -q '.state' 2>/dev/null || echo "UNKNOWN")

if [ "$ISSUE_STATE" = "CLOSED" ]; then
    echo "✓ Issue #$ISSUE_NUM is CLOSED"
else
    echo "⚠️  Issue #$ISSUE_NUM is still $ISSUE_STATE"
    echo "Closing issue..."
    gh issue close "$ISSUE_NUM" --comment "Closed via task-done.sh" 2>/dev/null || true

    # Verify again
    ISSUE_STATE=$(gh issue view "$ISSUE_NUM" --json state -q '.state' 2>/dev/null || echo "UNKNOWN")
    if [ "$ISSUE_STATE" = "CLOSED" ]; then
        echo "✓ Issue #$ISSUE_NUM is now CLOSED"
    else
        echo "❌ FAILED to close issue #$ISSUE_NUM - close manually!"
        exit 1
    fi
fi

echo ""
echo "=== Done ==="
echo "Issue #$ISSUE_NUM closed. PR merged to develop."
echo "Run ./scripts/deploy.sh when ready to deploy."
